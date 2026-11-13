.PHONY: validate regenerate regenerate-check release-check store-verification-v2-check

store-verification-v2-check:
	go test -p=1 -parallel=1 ./tools/check-store-verification-v2
	go run -p=1 ./tools/check-store-verification-v2 -root .

validate:
	python3 tools/fixture_environment.py python3 tools/validate.py
	python3 -B -m unittest discover -s tools -p 'test_*.py'
	python3 tools/fixture_environment.py go test ./tools/...

regenerate:
	python3 tools/fixture_environment.py go run ./tools/generate-vectors -root .

regenerate-check:
	python3 tools/fixture_environment.py python3 tools/validate.py --release-history-only
	python3 tools/fixture_environment.py go run ./tools/generate-vectors -root .
	python3 tools/fixture_environment.py git diff --exit-code -- conformance/v1 conformance/candidate.json conformance/go-native-controls-v2 conformance/skillfile-sources-v1/manifest.json conformance/draft-sources-v2/manifest.json release/1.0.0-rc.14.json

release-check: validate regenerate-check
	test -n "$(VERSION)"
	python3 tools/fixture_environment.py python3 tools/release_gate.py --version "$(VERSION)" --commit HEAD
