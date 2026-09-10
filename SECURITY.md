# Security — skill-abi

Report vulnerabilities privately to the maintainer (see GOVERNANCE.md)
before public disclosure.

Rules enforced in CI (`secret scan` job):
- no API keys, tokens, bearer credentials, or private keys in the tree
- no live chat/user identifiers (fixtures only)
- demo signing keys in this repo are explicitly NOT trust roots

Signing: local ed25519 demo flow documents mechanics only. Production
trust requires Sigstore-backed identity; the payload format is
designed to survive that upgrade unchanged.

Threat model note: a skill whose permitted effect is read-only cannot
mutate merely because the runtime exposes write tools — enforced by
the effect checker (`src/sabi/effects.py`), tested in
`tests/test_effects.py`.
