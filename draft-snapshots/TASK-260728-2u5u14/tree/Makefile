.PHONY: validate regenerate regenerate-check release-check

validate:
	python3 tools/validate.py
	python3 -B -m unittest discover -s tools -p 'test_*.py'
	go test ./tools/...

regenerate:
	go run ./tools/generate-vectors -root .
	go run ./tools/generate-external-repository-corpus -root .

regenerate-check:
	go run ./tools/generate-vectors -root .
	go run ./tools/generate-external-repository-corpus -root .
	git diff --exit-code -- conformance/v1 release/1.0.0-rc.5.json
	git diff --exit-code -- interop/rc5/external-repository

release-check: validate regenerate-check
	test -n "$(VERSION)"
	python3 tools/release_gate.py --version "$(VERSION)" --commit HEAD
