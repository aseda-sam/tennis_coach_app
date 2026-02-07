---
name: notion-learning-capture
description: Captures development learnings and insights to a Notion page. Use when the user says "capture learning", "add to learnings", "save this to learnings", or similar.
disable-model-invocation: true
---

# Notion Learning Capture

When the user asks to capture a learning, document it in Notion using this workflow.

## Process

1. **Summarize the learning** using this structure:

   - **Context**: When/where this applies
   - **Key Insight**: Main takeaway or technique
   - **Practical Application**: How to use it
   - **Benefits**: Why this matters (bullet points)
   - **Code Example**: Practical demonstration (if applicable)

2. **Add to Notion** using the Notion MCP tool to update the target page:

   - **Page ID**: `24ee302b-ac4c-815f-ae3b-d872d179e49c`
   - **Page Title**: "Learnings from Cursor"
   - Insert after existing learnings; use proper Notion-flavored Markdown

3. **Confirm** to the user that the learning was captured.

## Template

````markdown
### [Learning Title] - [Month Year]

**Context**: [When/where this applies]

**Key Insight**: [Main takeaway]

**Practical Application**: [How to use it]

**Benefits**:

- [Benefit 1]
- [Benefit 2]

**Code Example** (if applicable):

```language
// Code example here
```
````

```

## Notes

- Add new learnings after existing ones (chronological order).
- Use date format "Month Year" (e.g. January 2025).
- Keep summaries concise; include code when it helps.
```
