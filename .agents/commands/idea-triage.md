---
description: Triage raw product/app notes into a prioritized backlog (Now / Next / Later / Parking Lot).
---

# Idea Triage

## Workflow

1. Capture the raw text verbatim in `ideas/inbox.md` with today's date.
2. Split ideas into atomic items (one problem/outcome per item).
3. Score each item using the rubric below.
4. Produce `ideas/triaged.md` with these sections only:
   - Now (highest leverage)
   - Next
   - Later
   - Parking Lot
5. For each item, include:
   - Problem statement
   - Proposed solution
   - Why now
   - Effort (`S`, `M`, `L`)
   - Dependencies
   - First shippable step
6. Add a short "Assumptions to validate" list at the end.

## Scoring Rubric

Score each item 1–5 on each dimension:

- **User value:** Does this help users practice better or more consistently?
- **Strategic fit:** Does it align with practice-first, progressive disclosure, coach-prep positioning?
- **Learning value:** Will this produce data/feedback that improves product quality?
- **Build effort:** 5 = easiest, 1 = hardest.
- **Dependency risk:** 5 = independent, 1 = heavy dependencies.

`priority = user_value + strategic_fit + learning_value + build_effort + dependency_risk`

| Score | Band        |
| ----- | ----------- |
| 21–25 | Now         |
| 16–20 | Next        |
| 11–15 | Later       |
| ≤10   | Parking Lot |

## Output Rules

- Prefer ruthless simplification over completeness.
- Merge duplicates; keep strongest phrasing.
- Keep each item under 8 lines.
- If scope is too broad, split into separate backlog items.
- If the note is unclear, preserve it in Parking Lot with one clarifying question.

## Tennis App Defaults

- Prioritize features that increase practice consistency and coaching usefulness.
- Favor mobile-compatible read/reflect workflows over heavy mobile editing/video tools.
- Prefer instrumentation that improves model/heuristic quality from real user edits.

---

$ARGUMENTS
