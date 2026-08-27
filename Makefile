.PHONY: validate validate-hardened regenerate regenerate-hardened regenerate-check regenerate-hardened-check release-check

validate:
	python3 tools/validate.py
	python3 tools/validate_hardened.py
	python3 -B -m unittest discover -s tools -p 'test_*.py'
	go test ./tools/...

validate-hardened:
	python3 tools/validate_hardened.py

regenerate:
	go run ./tools/generate-vectors -root .

regenerate-hardened:
	go run ./tools/generate-hardened -root .

regenerate-check:
	go run ./tools/generate-vectors -root .
	git diff --exit-code -- conformance/v1 release/1.0.0-rc.5.json

regenerate-hardened-check:
	go run ./tools/generate-hardened -root .
	git diff --exit-code -- conformance/hardened release/hardened-1.0.0-rc.1.json
	git diff --exit-code -- conformance/v1 release/1.0.0-rc.5.json

release-check: validate regenerate-check
	test -n "$(VERSION)"
	python3 tools/release_gate.py --version "$(VERSION)" --commit HEAD
