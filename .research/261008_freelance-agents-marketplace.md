# Research note: a freelance-agents marketplace on a dedicated carrier server

- Date: 2026-10-08. Owner: ivan-curator. Status: evaluation only (the owner's brief, item 6); no decision proposed yet.
- Inputs: wiki `session-host/architecture.ru.md` §7.9–7.10 (onboarding, the join point, the two-domain federation test), the owners' call digest 2026-10-07 (Q13 federation), VISION v1.3 §0 (D-R6 carriers), CIP-0009 (the join handshake), relux-works/a2a-swarm (agent cards in `#lobby`, rooms per project).

## The idea, restated

A carrier server dedicated to **freelance agents**. Agents publish their cards there: skills, budgets, availability. Project servers come to post task boards or requests and look for remote workers. When a freelance agent answers and the terms are agreed, the agent goes — under its freelance-server identity — through the project's handshake (CIP-0009) and then joins the project room as a remote worker (CIP-0008 on its own machine).

## What exists that this would reuse

- **Agent cards and rooms** already exist in a2a (`agents/<name>.md`, `#lobby`, project rooms, `kind=offer|request|accept|decline` events). A marketplace is a Space with a card room and an offers room, plus two schemas.
- **Federation** is what Matrix does; the owners agreed to keep it as the reference two-domain test after the single-host MVP (digest Q13; architecture §7.10). A freelance server is a third domain of the same shape.
- **Identity** is not the carrier identity. The trust identity of a worker is its pinned key (architecture §7.2, §7.9); the Matrix id `@agent:freelance.example` is a carrier address. CIP-0009's handshake binds the key to the project; the marketplace only has to bind the card to the key (a signed card).
- **Credentials** stay with the freelancer: they run on their own machine with their own provider subscription (CIP-0010 C5). The project never pays for the model and never holds the freelancer's credentials.

## Feasibility

| Aspect | Assessment |
|---|---|
| Transport and rooms | Feasible now with a2a: one Space on a dedicated homeserver (for example `agents.<our domain>`), a `#cards` room (one signed card event per agent, replaceable), a `#requests` room (project posts), per-deal threads. Federation with project servers is standard Matrix. |
| Card schema | `swarma-agent-card/1`: `{key_id, name, skills[], harness, model class, budget {tokens/day, hours}, availability window, price or none, contact, sig}`. Signed by the agent's key; the key is the one it will later pin in a project. |
| Offer and acceptance | `swarma-offer/1` from a project (task class, repo visibility, expected volume, review rule, expiry) and `swarma-accept/1` from the agent, both signed. Acceptance ends with the project issuing a CIP-0009 invitation to the agent's declared contact. Nothing else is automated. |
| Trust and reputation | Reputation = signed receipts: an accepted outcome proposal (our board) produces a `swarma-receipt/1` signed by the project's root, published by the agent on its card if it wants. Receipts are verifiable across servers because they are signed by the project root whose fingerprint is in DNS (CIP-0009 D6). No central score. |
| Sybil and spam | Invitation-only onboarding to the marketplace (an existing member vouches, signed), rate limits on offers, and the fact that a project's handshake still requires a human fingerprint check. A stake or fee is possible later; not needed to start. |
| Privacy | A project should post only tasks it is willing to show to strangers (public repositories, or redacted snapshots). The task snapshot a remote worker receives is a projection of one element (architecture §7.9); for marketplace work the orchestrator must choose a *public* projection. This is a policy on the project side, not a marketplace feature. |
| Vendor terms | The freelancer uses their own subscription for their own harness on their own machine: "one person = one subscription" holds. Nothing in the marketplace shares credentials. |
| Payment | Out of scope for the first iteration: budgets are declared in tokens and hours; money, if any, is settled outside. |
| Where it fits the plan | After the single-host MVP and the two-domain federation test (architecture §11.4, §7.10). It is the third domain of that test, with an unknown party instead of a known one. |

## Risks and open points

1. **Liability and expectations.** A marketplace implies obligations (quality, payment, data handling) the platform does not want yet. Start as "a room where cards and offers are signed", not as a service with guarantees.
2. **Task leakage.** The main real risk: an orchestrator posting a private snapshot to an unknown agent. Mitigation: a `visibility: public` flag on the offer that the orchestrator must set, and a refusal to post a snapshot of a private repository to a marketplace thread.
3. **Quality of results.** Results are outcome *proposals* reviewed by our reviewers like any other; a freelance agent never lands anything.
4. **Abuse of the project's workplace.** The remote workplace policy (relux-works/remote-workplace v2.1: tools, write scope, network mode, limits) bounds what a freelancer can do on our host; a marketplace worker should get a stricter policy template than a known partner.
5. **Identity continuity.** A freelancer that loses its key loses its reputation; that is correct and should be documented.

## Recommendation (for the owners' review, not a decision)

Feasible and cheap at the room-and-schema level; the hard parts (handshake, lockdown, workplace policy, signed receipts) are the same parts the remote-worker design already needs. Sequence: single-host MVP → two-domain federation test with a known partner → a marketplace Space with signed cards and offers → invitation-only public opening. Do not build payment, scoring or dispute machinery first.
