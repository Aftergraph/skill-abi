# Rulesets — Aftergraph org

These JSON files define GitHub rulesets for the repo. Each file is a
**declarative record of the intended configuration**. Apply them via the
GitHub API (requires org-owner token):

```bash
# List existing rulesets
gh api repos/Aftergraph/skill-abi/rulesets

# Create/update a ruleset
gh api -X POST repos/Aftergraph/skill-abi/rulesets \
  --input .github/rulesets/<file>.json
```

## Files

| File | Target | Purpose |
|------|--------|---------|
| `main-branch.json` | `refs/heads/main` | PR + merge queue + 3 status checks (test, secrets, supply-chain) |
| `release-tags.json` | `refs/tags/v*` | Tag immutability + status checks on tags |

## Merge policy notes

- `required_approving_review_count: 0` is intentional — the Aftergraph org
  uses merge queue (ALLGREEN) as the primary gate; the org-level policy
  prefers automated validation over human review count.
- `bypass_actors: []` — no actors are exempted. Emergency bypass requires
  direct org-owner ruleset API edit with audit trail.
- `dismiss_stale_reviews_on_push: true` — a new push invalidates previous
  reviews.
- `required_review_thread_resolution: true` — all conversations must be
  resolved before merge.
- 3 required status contexts: `test`, `secrets`, `supply-chain`.
