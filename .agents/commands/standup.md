---
description: Morning standup — read the backlog and issues, suggest what to work on today.
---

# Standup

Trigger phrases:
- "good morning"
- "hello"
- "what should we work on?"
- "standup"
- "what's next?"

## Workflow

1. Read `backlog/issues.md` and `backlog/triaged.md`.
2. Check `git log --oneline -20` and recent merged PRs to identify work that has shipped.
3. **Cleanup pass:** Cross-reference shipped work against both backlog files:
   - Remove any issues from `issues.md` that are clearly resolved (matching feature/fix is in git history).
   - Remove or move to a "Done" comment any items in `triaged.md` that have shipped.
   - If you remove anything, list each removed item in chat so the user knows what was cleaned up.
4. Check `git branch` and `git status` for any in-progress work.
5. Summarize the current state in 3–5 lines:
   - Any open issues in "Fix now" or "Fix next"
   - Top 2–3 items from the "Now" tier in triaged.md
   - Any uncommitted or in-progress branch work
6. Recommend **one thing to start with** — prefer:
   - "Fix now" issues over everything else
   - Small trust/bug fixes over new features (momentum + trust)
   - Items with no unresolved dependencies
7. If the recommended item needs clarification or scoping, suggest entering plan mode.
8. Keep the whole response under 20 lines. No preamble — get straight to it.

## Tone

Direct and action-oriented. Like a co-founder standup, not a status report.

---
