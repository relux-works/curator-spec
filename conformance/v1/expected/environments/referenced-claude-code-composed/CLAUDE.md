<!--
curator-root-context-v2
root: companyA 2.3.0 commit 0123456789abcdef0123456789abcdef01234567
member: companyA 2.3.0 commit 0123456789abcdef0123456789abcdef01234567 weight 100
member: personal 0.3.0 state sha256:abababababababababababababababababababababababababababababababab weight 1000 overlay
precedence: winner=higher-weight placement=winner-last
lock: sha256:0305581b4f24d74ce271f9809d24f77b794b5ef9ad004bcc5c398fa2ea2e54ab
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
