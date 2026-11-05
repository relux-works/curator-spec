# Package-overlay tag proposal fixtures

These synthetic metadata fixtures accompany [CIP-0030](../../cips/CIP-0030-package-prefixed-overlay-ranges.md).
They emit no complete schema and remain outside frozen release vectors. The
maintainer selected context lock version 6 conditional on version 5 landing
first; these fixtures do not establish that prerequisite or carrier.

Run the bounded checker and its controls:

```sh
go test ./tools/check-overlay-range-proposal -count=1
go run ./tools/check-overlay-range-proposal -root .
```

The model filters exact tag prefixes, compares strict stable version triples
for `*` or `>=0.1.17 <1.0.0`, checks the selected manifest, and models exact
pin comparison on replay. Prerelease and build-bearing tags are outside those
stable ranges. Each case states its expected selection, diagnostic and warning.
The `lock` object is an evidence projection, not the complete version-6
context lock schema. The checker rejects unsupported ranges; it does not reinterpret
them as the supported subset.

The corpus has both accepting and refusing controls. Unit controls deliberately
corrupt expected success and refusal results, require the exact mismatch, and
check that later cases still execute. Model tests plant sibling/plain-tag
selection, removed manifest checks and removed strict pin comparison through
single input defects, requiring their specific refusal and a restored positive.

No actual Git fetch, signature verification, source allowlist, general semver
parser, platform extraction, native-home write or profile install runs here.
Claims about no accepted-state writes require the real CLI/integration controls
listed in the CIP. A fixture pass is only proposal consistency evidence.
