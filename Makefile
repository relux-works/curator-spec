.PHONY: validate regenerate regenerate-check

validate:
	python3 tools/validate.py
	go test ./tools/...

regenerate:
	go run ./tools/generate-vectors -root .

regenerate-check:
	go run ./tools/generate-vectors -root .
	git diff --exit-code -- conformance/v1
