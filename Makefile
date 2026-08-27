.PHONY: validate regenerate regenerate-check release-check boundary-probe boundary-probe-controls

validate:
	python3 tools/validate.py
	python3 -B -m unittest discover -s tools -p 'test_*.py'
	go test ./tools/...

regenerate:
	go run ./tools/generate-vectors -root .

regenerate-check:
	go run ./tools/generate-vectors -root .
	git diff --exit-code -- conformance/v1 conformance/next release/1.0.0-rc.5.json

release-check: validate regenerate-check
	test -n "$(VERSION)"
	python3 tools/release_gate.py --version "$(VERSION)" --commit HEAD

# The section 4.2.1.2 boundary probe. It needs a real Go toolchain of each
# family in the manager's compatibility set, so it is not part of `validate`;
# `tools/validate.py` checks that the probe is present and that the fixture
# alignment table agrees with the probe's own case table.
boundary-probe:
	test -n "$(GO_TOOLCHAINS)"
	go run ./tools/toolchain-boundary-probe $(foreach bin,$(GO_TOOLCHAINS),-go $(bin))

# Every control is required to fail. A control that passes means the property it
# guards is no longer being tested, so this target inverts each exit status.
boundary-probe-controls:
	test -n "$(GO_TOOLCHAINS)"
	@for control in open-classifier unrelated-command-failure patch-prerelease-compared c-equals-upstream; do \
		echo "== expected-red control: $$control"; \
		if go run ./tools/toolchain-boundary-probe $(foreach bin,$(GO_TOOLCHAINS),-go $(bin)) -red $$control >/dev/null 2>&1; then \
			echo "control $$control passed; the property it guards is no longer being tested"; exit 1; \
		fi; \
	done
	@echo "== expected-red control: tidy-exit"
	@if go run ./tools/toolchain-boundary-probe $(foreach bin,$(GO_TOOLCHAINS),-go $(bin)) -semantic tidy-exit >/dev/null 2>&1; then \
		echo "control tidy-exit passed; the retired classifier is no longer failing"; exit 1; \
	fi
	@echo "all five controls failed as required"
