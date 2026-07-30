.PHONY: validate regenerate regenerate-check release-check

validate:
	python3 tools/validate.py
	python3 -B -m unittest discover -s tools -p 'test_*.py'
	go test ./tools/...

regenerate:
	go run ./tools/generate-vectors -root .

regenerate-check:
	go run ./tools/generate-vectors -root .
	git diff --exit-code -- conformance/v1 release/1.0.0-rc.5.json release/1.0.0-rc.6.json

release-check: validate regenerate-check
	test -n "$(VERSION)"
	python3 tools/release_gate.py --version "$(VERSION)" --commit HEAD
