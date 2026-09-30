<!--
curator-root-context-v2
root: companyA 2.3.0 commit 0123456789abcdef0123456789abcdef01234567
member: companyA 2.3.0 commit 0123456789abcdef0123456789abcdef01234567 weight 100
member: personal 0.3.0 state sha256:abababababababababababababababababababababababababababababababab weight 1000 overlay
precedence: winner=higher-weight placement=winner-last
lock: sha256:8c5bbca87744959090345236e6947047c65475b533ff90fd25c1f01d261a8df6
generated: Curator Protocol environments revision 1 (https://github.com/relux-works/curator-spec)
notice: generated file; direct edits are unsupported and are detected as drift; update the source profile repository or its composed profiles instead
-->

---

## Context: companyA 2.3.0

@.agent-context/modules/companyA/00-base.md

@.agent-context/modules/companyA/10-style.md

@.agent-context/modules/companyA/20-claude.md

---

## Context: personal 0.3.0

@.agent-context/modules/personal/00-base.md
