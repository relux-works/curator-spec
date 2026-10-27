// A synthetic specification benchmark, not Curator's admission or launcher implementation.
package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"time"
)

type provenance struct {
	Source string `json:"source"`
	Class  string `json:"class"`
}
type entry struct {
	Name       string       `json:"name"`
	Spellings  []string     `json:"spellings"`
	Provenance []provenance `json:"provenance"`
}
type artifact struct {
	Schema        int               `json:"schema_version"`
	Version       string            `json:"inventory_version"`
	Normalization string            `json:"normalization"`
	Extractor     string            `json:"extractor_version"`
	ExtractorHash string            `json:"extractor_sha256"`
	Pins          []json.RawMessage `json:"source_pins"`
	Patterns      []json.RawMessage `json:"patterns"`
	Entries       []entry           `json:"entries"`
}
type identity struct {
	Version       string `json:"version"`
	Hash          string `json:"sha256"`
	Normalization string `json:"normalization"`
}
type metadata struct {
	Schema    int      `json:"schema_version"`
	Inventory identity `json:"command_inventory"`
	Count     int      `json:"entry_count"`
	Bytes     int      `json:"bytes"`
}
type directory struct {
	path string
	info os.FileInfo
}
type index map[string]struct{}

func digest(raw []byte) string {
	sum := sha256.Sum256(raw)
	return "sha256:" + hex.EncodeToString(sum[:])
}
func load(path string, expected metadata) (index, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	raw, err := io.ReadAll(io.LimitReader(f, 16*1024*1024+1))
	if err != nil {
		return nil, err
	}
	if len(raw) != expected.Bytes || len(raw) > 16*1024*1024 || digest(raw) != expected.Inventory.Hash {
		return nil, errors.New("inventory_digest")
	}
	var a artifact
	d := json.NewDecoder(bytes.NewReader(raw))
	d.DisallowUnknownFields()
	if err = d.Decode(&a); err != nil {
		return nil, err
	}
	if a.Schema != 1 || a.Version != expected.Inventory.Version || a.Normalization != "ascii-fold-wrapper-suffix-v1" || a.Normalization != expected.Inventory.Normalization || a.Extractor != "protected-command-inventory/1" || len(a.Entries) != expected.Count || len(a.Entries) > 100000 {
		return nil, errors.New("inventory_identity")
	}
	// Digest authenticates the exact previously schema/CCJ-validated release bytes. No generic untrusted-source parser is timed here.
	keys := make(index, len(a.Entries))
	previous := ""
	for _, e := range a.Entries {
		if e.Name <= previous || len(e.Name) > 128 {
			return nil, errors.New("entry_order")
		}
		keys[e.Name] = struct{}{}
		previous = e.Name
	}
	return keys, nil
}
func normalize(name string) string {
	name = strings.ToLower(name) // Benchmark inputs are validated ASCII literals.
	for {
		changed := false
		for _, suffix := range []string{".exe", ".com", ".bat", ".cmd", ".ps1"} {
			if strings.HasSuffix(name, suffix) {
				name = strings.TrimSuffix(name, suffix)
				changed = true
				break
			}
		}
		if !changed {
			return name
		}
	}
}
func check(names []string, dirs []directory, suffixes []string, keys index) error {
	for _, dir := range dirs {
		info, err := os.Lstat(dir.path)
		if err != nil {
			return err
		}
		if !info.IsDir() || !os.SameFile(info, dir.info) {
			return errors.New("admission_changed")
		}
	}
	seen := make(map[string]bool, len(names))
	for _, name := range names {
		key := normalize(name)
		if seen[key] {
			return errors.New("ambiguous_export")
		}
		seen[key] = true
		if key == "curator" || strings.HasPrefix(key, "curator-") {
			return errors.New("reserved_namespace")
		}
		if _, present := keys[key]; present {
			return errors.New("static_overlap")
		}
		for _, dir := range dirs {
			for _, suffix := range suffixes {
				info, err := os.Lstat(filepath.Join(dir.path, name+suffix))
				if errors.Is(err, os.ErrNotExist) {
					continue
				}
				if err != nil {
					return err
				}
				// This bounded miss benchmark admits no links/forwarder exemptions; they must be qualified separately.
				if info.Mode()&os.ModeSymlink != 0 {
					return errors.New("admission_unsafe_link")
				}
				if info.Mode().IsRegular() && (runtime.GOOS == "windows" || info.Mode().Perm()&0111 != 0) {
					return errors.New("base_path_collision")
				}
			}
		}
	}
	return nil
}
func must(err error) {
	if err != nil {
		panic(err)
	}
}
func ms(d time.Duration) float64 { return float64(d.Nanoseconds()) / 1e6 }
func main() {
	inventoryPath := flag.String("inventory", "data/protected-commands/v1/inventory.json", "reviewed canonical artifact")
	metadataPath := flag.String("metadata", "data/protected-commands/v1/artifact.json", "reviewed expected identity")
	mode := flag.String("suffix-mode", "native", "native executable lookup or portable-stress (all six spellings)")
	flag.Parse()
	// Fixture creation and reading the trusted embedded-identity equivalent are outside the measured checks.
	var expected metadata
	raw, err := os.ReadFile(*metadataPath)
	must(err)
	must(json.Unmarshal(raw, &expected))
	root, err := os.MkdirTemp("", "protected-inventory-benchmark-")
	must(err)
	defer os.RemoveAll(root)
	dirs := make([]directory, 12)
	for i := range dirs {
		path := filepath.Join(root, fmt.Sprintf("base-%02d", i))
		must(os.Mkdir(path, 0700))
		info, err := os.Lstat(path)
		must(err)
		dirs[i] = directory{path, info}
	}
	names := make([]string, 64)
	for i := range names {
		names[i] = fmt.Sprintf("acme-benchmark-command-%02d", i)
	}
	suffixes := []string{""}
	if runtime.GOOS == "windows" || *mode == "portable-stress" {
		suffixes = []string{"", ".exe", ".com", ".bat", ".cmd", ".ps1"}
	}
	if *mode != "native" && *mode != "portable-stress" {
		panic("unknown suffix mode")
	}
	start := time.Now()
	keys, err := load(*inventoryPath, expected)
	must(err)
	must(check(names, dirs, suffixes, keys))
	cold := ms(time.Since(start))
	samples := make([]float64, 31)
	for i := range samples {
		start = time.Now()
		must(check(names, dirs, suffixes, keys))
		samples[i] = ms(time.Since(start))
	}
	// Independent negative and positive controls: the final candidate must detect a real executable and preserve its bytes.
	plant := filepath.Join(dirs[len(dirs)-1].path, names[len(names)-1]+suffixes[len(suffixes)-1])
	payload := []byte("synthetic collision witness\n")
	must(os.WriteFile(plant, payload, 0700))
	before, err := os.Lstat(plant)
	must(err)
	err = check(names, dirs, suffixes, keys)
	if err == nil || err.Error() != "base_path_collision" {
		panic("collision control not detected")
	}
	after, err := os.Lstat(plant)
	must(err)
	postimage, err := os.ReadFile(plant)
	must(err)
	if !os.SameFile(before, after) || !bytes.Equal(payload, postimage) {
		panic("preimage changed")
	}
	must(os.Remove(plant))
	must(check(names, dirs, suffixes, keys))
	sorted := append([]float64(nil), samples...)
	sort.Float64s(sorted)
	max := sorted[len(sorted)-1]
	pass := cold <= 20 && max <= 20
	result := map[string]any{"schema_version": 1, "inventory": expected.Inventory, "scope": "synthetic local miss check; cold digest/read/decode/index plus probes; warm immutable index; not a Curator launcher qualification", "go_version": runtime.Version(), "platform": runtime.GOOS + "/" + runtime.GOARCH, "commands": len(names), "directories": len(dirs), "suffixes": len(suffixes), "suffix_mode": *mode, "candidate_probes_per_pass": len(names) * len(dirs) * len(suffixes), "warm_runs": len(samples), "cold_ms": cold, "warm_ms": samples, "warm_median_ms": sorted[len(sorted)/2], "warm_p95_ms": sorted[29], "warm_max_ms": max, "budget_ms": 20, "budget_pass": pass, "collision_control": "base_path_collision", "positive_control": "ok after fixture removal", "preimage_unchanged": true}
	out, err := json.MarshalIndent(result, "", "  ")
	must(err)
	fmt.Println(string(out))
	if !pass {
		os.Exit(1)
	}
}
