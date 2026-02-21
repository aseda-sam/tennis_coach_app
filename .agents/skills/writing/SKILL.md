---
name: writing
description: Two-part writing skill for the Tennis Coach App Substack series. Use "capture" to save story seeds from dev sessions. Use "compose" for guidance on structuring articles.
---

# Writing

This skill covers both sides of the writing workflow: capturing raw material from dev sessions, and composing it into Substack articles.

---

## Part 1: Capture — Story Seeds

Captures raw material from conversations that would otherwise be lost: the *why* behind decisions, pivots, dead-ends, and interesting moments that become Substack article fodder.

### When to capture

- User says "capture this", "save that idea", "log this pivot", "this would make a good article bit"
- Before a chat ends and there's context worth preserving
- When a decision, trade-off, or surprise emerges mid-conversation
- When something went wrong (or unexpectedly right)

### Workflow

1. Ask the user: "What's the headline version of this moment in one sentence?"
2. Gather context from the current conversation — extract the key facts, the reasoning, the surprise or tension
3. Ask which seed type best fits (see types below) — or infer it
4. Write the seed file to `writing/story-seeds/` using the template
5. Confirm the file path to the user

### Seed types

| Type | When to use |
|------|------------|
| `pivot` | Changed direction — what was plan A, what's plan B, why |
| `decision` | Chose between options — what were they, what tipped the balance |
| `dead-end` | Tried something that didn't work — what was learned |
| `aha` | Realised something non-obvious — the insight and what prompted it |
| `challenge` | Hit a hard problem — what made it hard, how (or whether) it was solved |
| `design-philosophy` | Made a deliberate product/UX choice — what it is and why |

### File naming

`writing/story-seeds/YYYY-MM-DD-short-slug.md`

Use today's date. Slug: 3-5 lowercase words with hyphens.

### Template

```markdown
---
date: YYYY-MM-DD
type: pivot | decision | dead-end | aha | challenge | design-philosophy
title: One-sentence headline
tags: [tennis, serve-detection, architecture, ux, ...]  # pick what fits
potential_article: yes | maybe | background
---

## What happened

[2-4 sentences: the concrete facts. What was being built, what happened, what changed.]

## Why it's interesting

[1-3 sentences: the human or intellectual angle. What does this reveal about the project, the problem space, or the builder?]

## The tension or surprise

[Optional. What made this a real moment — a failed assumption, a surprising constraint, a counter-intuitive choice?]

## Raw context

[Paste relevant quotes, commit messages, code snippets, or chat excerpts. Keep it loose — this is raw material.]

## Possible article angle

[One sentence on how this could become a story beat, a section of an article, or a standalone piece.]
```

### Capture notes

- Don't over-polish seeds — they're raw material, not drafts
- One seed per distinct moment; don't bundle unrelated events
- `potential_article: yes` = strong standalone story; `maybe` = good supporting detail; `background` = context only
- See `writing/LTA-COACHING-NOTES.md` for LTA course context and design implications

---

## Part 2: Compose — Article Structure

Reference for structuring Substack articles about the Tennis Coach App project.

### Series premise

Developer + amateur tennis player builds an app to analyse and improve their own serve.
*And* decides to get LTA Level 1 coaching certification to understand what coaching actually is.
The story is honest, in-progress, and told as it happens — not in retrospect.

**Voice:** First person, curious, technically literate but not showing off.
**Audience:** Developers who build things for themselves, tennis players who like tech, people who've ever tried to learn a skill as an adult.

**The hook:** I can't afford regular coaching, so I'm building the coach I can't afford. But first, I need to learn how to coach.

### Article structure template

```
1. Hook (100-150 words)
   - One concrete scene or confession
   - Bridge to why software is the answer

2. The idea / what you built (150-200 words)
   - What the app does, in plain language
   - The specific problem it's solving
   - Optional: show a screenshot/GIF

3. The interesting bit (200-300 words)
   - The pivot, the challenge, the surprise, the design choice
   - Mine story-seeds/ for this section

4. The honest status (100 words)
   - What's not working yet
   - What you don't know
   - This is trust-building, not a disclaimer

5. What's next (75 words)
   - 2-3 concrete things on the horizon
   - Tease the next article

6. Question for readers + CTA (50 words)
   - One open question to invite response
   - Subscribe nudge, GitHub link
```

### Known article ideas (backlog)

- **Article 1:** Introduction — what the app is, why it exists, the hook. Mention the LTA course as a character beat.
- **Article 2:** "I'm Building a Tennis App, So I Decided to Become a Coach" — LTA L1, progressive teaching, LXD background, the insight that the app needs to *teach*, not just measure
- **Article 3:** The serve window problem — what even is a serve in a video?
- **Article 4:** Biomechanics vs scores — why the output changed
- **Article 5:** One recommendation — the design philosophy of limiting output
- **Article 6:** "Where This Fits in the Tennis Tech Landscape" — SwingVision does match stats, I do serve coaching; staying narrow is a choice
- **Article 7:** Does it actually make me better? (future — needs real testing and LTA insights applied)

### Story seeds index

Story seeds live in `writing/story-seeds/`. Each has frontmatter with:
- `type`: pivot | decision | dead-end | aha | challenge | design-philosophy
- `potential_article`: yes | maybe | background

Mine them when writing. A single article usually draws on 3-5 seeds.

### Tone guardrails

- Don't explain every technical choice — explain the *human* reason behind it
- Name the failures and confusion — that's more interesting than the solutions
- Keep jargon minimal in openers; earn technical depth later in the piece
- Short paragraphs. Substack reads on mobile.
- Keep narration in first person (`I`, `me`, `my`); avoid second-person narration (`you`) unless directly asking readers a question.
