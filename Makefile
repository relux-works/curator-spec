.PHONY: validate regenerate regenerate-check release-check

validate:
	python3 tools/validate.py
	python3 -B -m unittest discover -s tools -p 'test_*.py'
	go test ./tools/...

regenerate:
	go run ./tools/generate-vectors -root .

regenerate-check:
	python3 tools/validate.py --release-history-only
	go run ./tools/generate-vectors -root .
	git diff --exit-code -- conformance/v1 conformance/candidate.json conformance/skillfile-sources-v1/manifest.json release/1.0.0-rc.14.json

release-check: validate regenerate-check
	test -n "$(VERSION)"
	python3 tools/release_gate.py --version "$(VERSION)" --commit HEAD
