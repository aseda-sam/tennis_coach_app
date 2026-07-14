---
description: Triage raw product/app notes into a prioritized backlog (Now / Next / Later / Parking Lot).
---

# Idea Triage

## Workflow

1. File each triaged item as an issue in Linear, team **S²Serve** (key `SERVE`): Now → Todo, Next/Later → Backlog, priority 2 serious / 3 concrete / 4 deferred (record the trigger in the body), Fibonacci estimate. Titles must make sense alone on a phone screen. If this session has no Linear access, stage the issues as a list for Aseda to file.
2. Split ideas into atomic items (one problem/outcome per item).
3. Score each item using the rubric below.
4. For each item, structure the issue body with these elements:
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

## Validation Checks (run after placing items)

- **No upward dependencies:** A Now item must not depend on a Next/Later item. If it does, either pull the dependency forward or call out the conflict.
- **Tier balance:** Each tier (especially Now) should not be 100% new surface area with nothing for existing users. Mix quick wins for current workflows alongside new capabilities.
- **Small trust-critical bugs go to Now:** Bugs that erode user trust in existing data (broken filters, wrong numbers) are cheap to fix and expensive to defer — default to Now regardless of score.

## Tennis App Defaults

- Prioritize features that increase practice consistency and coaching usefulness.
- Favor mobile-compatible read/reflect workflows over heavy mobile editing/video tools.
- Prefer instrumentation that improves model/heuristic quality from real user edits.

---
