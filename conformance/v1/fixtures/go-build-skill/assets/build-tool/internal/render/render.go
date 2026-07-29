package render

import (
	_ "embed"
	"strings"

	"example.com/curator/vendored/decorate"
)

//go:embed template.txt
var template string

//go:embed empty.txt
var empty []byte

func Message() string {
	_ = empty
	return decorate.Wrap(strings.TrimSpace(template)) + "\n"
}
