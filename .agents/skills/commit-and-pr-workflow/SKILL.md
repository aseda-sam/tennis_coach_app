---
name: commit-and-pr-workflow
description: Generates conventional commit messages, squash-merge messages, and PR titles/descriptions for this repo. Use when the user asks for a commit message, PR message, squash merge message, or to draft PR/commit text.
---

# Commit and PR Workflow

Generate commit messages, squash-merge messages, or PR text following this repo's conventions.

## Conventional Commits

Format: `<type>(<scope>): <description>`

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples**:

- `feat(serve): add LLM feedback to serve analysis`
- `fix(api): resolve ball tracking in low-light`
- `docs: update API docs for new endpoints`

**Scope** is optional; use when it clarifies the change (e.g. module or area).

## Squash Merge Message

When generating a **squash merge** message (e.g. for GitHub "Squash and merge"):

1. Review all commits on the branch.
2. One line: `type(scope): short summary` — match conventional format.
3. Blank line, then 1–3 bullet points summarizing the change set.
4. If there is a linked issue: `Closes #N` at the end.

**Example**:

```
feat(serve): add LLM coaching feedback (#123)

- Integrate LLM feedback service with serve attempts API
- Add feedback schema and evaluation tests
- Update docs for new feedback fields

Closes #100
```

Prefer shorter; use medium length only if 3+ distinct changes warrant it. Output plain text ready to paste into the squash-merge commit message field.

## PR Title and Description

When generating a **PR title and description**:

1. Review commits on the branch.
2. **Title**: One line, descriptive (can match intended squash message summary).
3. **Body**: Follow `.github/pull_request_template.md`:
   - Description + why + key design decisions
   - Type of change (bug fix / new feature / docs / refactor)
   - How it was tested
   - Checklist (contributing, ruff/eslint, docs, no secrets)
   - Related issues: `Closes #N`

Output complete markdown ready to paste into GitHub's PR description. Do not create a file; output in chat.

## Branch and Commit Policy

- **Never commit automatically** without explicit user approval.
- After suggesting a message, ask: "Should I commit these changes?" or equivalent.
- If the user says "don't commit yet" or similar, do not run git commit.
