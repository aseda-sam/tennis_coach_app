---
description: Triage bug reports and issues into a prioritized list with repro steps and fix direction.
---

# Issue Triage

Trigger phrases:
- "triage issues"
- "log issues"
- "bug triage"

## Workflow

1. File the bug in Linear, team **S²Serve** (key `SERVE`), with severity/effort in the body. If this session has no Linear access, stage it for Aseda to file.
2. Split into atomic issues (one bug/behavior per item).
3. For each issue, fill in the template below as far as possible from context + codebase search.
4. If the likely cause or fix scope is unclear after a quick codebase search, suggest entering plan mode to confirm the diagnosis with the user before writing a fix direction. Keep plan mode lightweight — just enough to confirm the right file/component and approach, not a full implementation plan.
5. Place each issue into a priority tier.

## Issue Template

```
- **<short title>**
  Symptom: What the user sees / what's wrong.
  Repro: Steps or conditions to trigger it (if known).
  Likely cause: Component/file/logic suspected (fill after codebase search).
  Fix direction: Brief approach — what to change and where.
  Severity: `critical` | `high` | `medium` | `low`
  Effort: `S` | `M` | `L`
```

## Priority Tiers

| Tier | Criteria |
|------|----------|
| Fix now | Data integrity, auth/security, or blocks core workflow. |
| Fix next | Visible UX bug, affects trust or usability but has workaround. |
| Fix later | Polish, cosmetic, edge-case annoyance. |

## Severity Guide

- **critical:** Data corruption, auth bypass, app crash on core path.
- **high:** Wrong data shown, broken filter/query, feature unusable in production.
- **medium:** UX annoyance, scroll/layout issue, non-blocking visual bug.
- **low:** Cosmetic, rare edge case, minor inconsistency.

## Output Rules

- Merge duplicates (the "me" filter issue and the "me" API endpoint issue may be the same root cause — check before splitting).
- Always search the codebase for the likely cause before writing the fix direction. Cite file paths.
- If a bug overlaps an existing SERVE issue, reference it rather than duplicating.
- Keep each issue under 8 lines.

## Output File

Update the SERVE issue when new information surfaces; one issue per bug, no duplicates.

---
