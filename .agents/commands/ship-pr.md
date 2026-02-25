# ship-pr

Intent:
- Execute the full delivery flow for the current branch: commit, push, open PR, verify checks, and merge.

Trigger phrases:
- "commit push PR merge"
- "ship it"
- "land this PR"

Execution steps:
1. Confirm the current branch is not `main`.
2. Review `git status --short`.
3. Stage and commit all intended changes with a concise message.
4. Push branch to origin.
5. Open/update a PR targeting `main`.
6. Wait for required CI checks to pass.
7. Merge using the repo-required strategy/policy.
8. Confirm merge commit and final branch/repo state.

Safety rules:
- Do not merge if required checks are failing.
- If branch protection blocks normal merge, use approved repo policy (`--auto` or `--admin`) only when explicitly authorized by the user.
- Keep the user informed if checks are pending for a long time.
