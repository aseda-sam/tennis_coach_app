# Visual Identity — Tennis Coach App

This document is the aesthetic north star. **Read this before writing any component, page, or CSS.** It gives the agent (and the developer) a shared vision to produce — not just rules about *how* to write CSS, but a clear picture of *what to produce*.

> **Name in testing:** The app is currently trialling the name **"Second Serve"** in the UI. The repo and codebase still use the old name. This will be confirmed or revisited after a few weeks of feedback.

---

## In one sentence

A clean, personal training log with richer tennis identity — high contrast, editorial whitespace, metrics as the hero, court-line textures, bold typography, and first-class annotation overlays.

---

## Aesthetic Direction: Richer Clean Sport

Light, confident, and editorial — with added tennis personality. Think of a well-designed sports magazine spread: generous margins, strong typography, content given room to breathe. Court-line patterns and a deep-blue accent connect the app to the sport without overwhelming the content.

**Key qualities:**

- **Light everywhere.** White surfaces, near-white backgrounds. Darkness is reserved for text and display numbers, not backgrounds.
- **Space signals importance.** Generous margins and padding say the content matters. Don't pack things in. Cramped UI feels cheap.
- **Typography carries the personality.** The fonts do the design work — not gradients, not color blocks, not decorative elements.
- **Green is earned.** The green accent is used for one thing: action and positive state. A primary button. A completed badge. A "you did something" moment. Not headers, not background sections, not decoration.
- **Court blue (`--color-court-blue`) adds wayfinding.** Active toggle states, breadcrumb hovers, and thumbnail highlights use court blue. It signals "you are here" and "this is tennis."
- **Court-line patterns add texture.** Subtle CSS grid lines at very low opacity (6%) appear on the analysis page background and stick-figure canvas. They whisper "court" without competing with content.
- **Numbers are the heroes.** In the analysis view, metric values dominate visually. Everything else — labels, borders, backgrounds — exists to frame them.
- **Annotations are first-class.** Toss height brackets, laterality arrows, and contact crosshairs use the annotation palette (cyan + magenta) with rounded-rect label backdrops. They appear in the stick-figure view and are designed to be beautiful, not just informative.

---

## Typography System

### Fonts

| Role | Font | Weights |
|------|------|---------|
| UI / Body | DM Sans | 300, 400, 500, 600, 700 |
| Metric display | DM Mono | 400, 500 |

**Why DM Sans over Inter:** DM Sans has slightly rounded geometry that feels sporty and approachable. Its 600 and 700 weights have more character at display sizes than Inter's equivalent. It reads cleanly at small sizes but has personality at heading sizes — Inter is neutral by design, DM Sans has a point of view.

**Why DM Mono for metrics:** Metric values are numbers. Numbers deserve a monospaced font so digits have consistent width and carry visual precision. DM Mono reads as "precise measurement" rather than "developer terminal" — it's cleaner and more contemporary than JetBrains Mono.

### Type Hierarchy

Apply these consistently across all views:

| Level | Token | Size | Weight | Font | Use |
|-------|-------|------|--------|------|-----|
| Hero metric | `--font-size-display-xl` | 3rem | 500 | DM Mono | Single standout number (e.g., contact time hero) |
| Large metric | `--font-size-display-lg` | 2.5rem | 500 | DM Mono | Primary metric values in analysis sidebar |
| Medium metric | `--font-size-display-md` | 2rem | 500 | DM Mono | Secondary metric values |
| Small metric | `--font-size-display-sm` | 1.5rem | 500 | DM Mono | Compact metric displays, timeline annotations |
| Page heading | `--font-size-5xl` | 1.6rem | 700 | DM Sans | Page titles (h1) |
| Section heading | `--font-size-4xl` | 1.25rem | 600 | DM Sans | Section/panel headers (h2) |
| Card title | `--font-size-xl` | 1rem | 600 | DM Sans | Card headers, group labels |
| Body | `--font-size-base` | 0.875rem | 400 | DM Sans | Body text, descriptions |
| Label | `--font-size-sm` | 0.8rem | 500 | DM Sans | Field labels, metric labels |
| Caption | `--font-size-xs` | 0.75rem | 400 | DM Sans | Timestamps, fine print |

**Metric label pattern** — always uppercase, `--letter-spacing-wide`, muted color:

```
2.4 s             ← DM Mono, display-md, --color-ink-heavy
CONTACT TIME      ← DM Sans, xs, uppercase, letter-spacing-wide, --color-text-muted
```

---

## Color Philosophy

The hex values are in `design-tokens.css`. This section explains the *intent* — what each part of the palette is *for*. Use this to make color decisions, not just the values.

### Green (`--color-primary: #00bc7d`)
**One job: action and positive state.** Primary action buttons (e.g., "Analyze", "Save"). Completed status badges. Positive metric highlights. If you're using green for brand identity, decoration, or a button that isn't a primary action — stop. The scarcity of green is what makes it work. The app logo and secondary CTAs like "Upload" use `--color-ink-heavy`, not green.

### Court Blue (`--color-court-blue: #1B4B7A`)
**One job: spatial identity and wayfinding.** Active segment in the view mode toggle. Header nav active tab. Breadcrumb hover color. Active thumbnail border. Scrubber accent. Edit-button hover accent on cards. It says "tennis court" without being literal. Use the `--soft` variant for hover backgrounds.

### Amber Gold (`--color-amber: #c8941a`)
**Second accent for non-action highlights.** Active nav tab state. Interesting data moments. Status indicators that aren't success/error. Think of it as "this is noteworthy but not a call to action." Not for primary buttons — those are either green (action) or ink-heavy (neutral CTA).

### Court Clay (`--color-court-clay: #D4784A`)
**Reserved.** Available for future court-surface theming or accent moments. Not currently used in active UI — kept in the palette for consistency.

### Ball Yellow (`--color-ball-yellow: #CCFF00`)
**Reserved.** A high-visibility accent for ball-tracking highlights. Not used in standard UI chrome.

### Annotation Palette
Three colors for canvas-rendered measurement overlays:
- `--color-annotation-primary` (#00D4FF) — cyan. Lines, brackets, labels, contact crosshair.
- `--color-annotation-accent` (#FF1493) — magenta. Ball trail, head dot.
- `--color-annotation-skeleton` (#00FF88) — green. Skeleton bones, phase pill.

### Ink Heavy (`--color-ink-heavy: #0a0f1a`)
**One job: display text with authority.** Large metric numbers. Hero headings where the text needs visual mass. Use instead of `--color-text` when a value needs to dominate the view. Not for body text — too heavy.

### Sand (`--color-sand: #f5f0e8`)
**One job: warmth without color.** Use as a background for "highlight" sections — a personal best, an onboarding card, a progress summary. Adds warmth without competing with the green accent. Sparingly: one such region per page, if at all.

### Everything else
- `--color-background` (#f8f5f1): warm parchment. The page canvas. Slightly warm so pure-white cards read as surfaces without needing shadows. Do not use cold blue-tinted backgrounds.
- `--color-surface` (#ffffff): cards, panels, modals. Crisp white.
- `--color-border` (#e5e7eb): the primary depth tool. Cards and dividers are defined by their border, not their shadow.
- `--color-text` (#101828): body text, card content, standard UI text.
- `--color-text-muted` (#4a5565): metadata, timestamps, metric labels.
- Semantic colors (error, warning, success, info): for their named purpose only.

### The depth system: borders, not shadows

**Use borders for:** cards, panels, inputs, form fields, dividers between sections.
**Use shadows for:** modals, popovers, dropdown menus, floating action buttons.

This is what makes Clean Sport look editorial rather than generic SaaS. Cards defined by a clean `1px solid --color-border` have more visual clarity than cards wearing heavy box-shadows. Reserve shadows for elements that need to appear *above* the page surface, not just distinct from it.

---

## Layout Grammar

These rules govern page structure. "Bad margins" and "UI component placement" issues almost always come from ignoring this.

### Container widths

Always place content inside one of three container widths:

| Context | Token | Value | Use |
|---------|-------|-------|-----|
| Standard content | `--layout-content-max-width` | 1200px | Video list, analysis dashboard, most pages |
| Narrow / focused | `--layout-narrow-max-width` | 720px | Forms, upload flow, auth, settings |
| Full page bound | `--layout-page-max-width` | 1440px | Outer absolute maximum (rarely relevant) |

**Standard page container pattern:**
```css
.page-container {
  max-width: var(--layout-content-max-width);
  margin: 0 auto;
  padding: 0 var(--layout-page-gutter);
}
```

`--layout-page-gutter` is `clamp(16px, 4vw, 48px)` — it scales with viewport so mobile gets 16px and desktop gets up to 48px without any breakpoint logic.

### Spacing rhythm

| Context | Token | Value |
|---------|-------|-------|
| Between major page sections | `--layout-section-gap` | 80px |
| Between cards in a grid | `--layout-card-gap` | 24px |
| Card grid column minimum | `--layout-card-grid-min` | 280px |

**Standard card grid pattern:**
```css
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(var(--layout-card-grid-min), 1fr));
  gap: var(--layout-card-gap);
}
```

### Page structure rules

1. **Every page has a page header** — a title (h1), optional subtitle, optional primary CTA. The header is inside the standard container, not floating.
2. **Content columns are always centered** — `margin: 0 auto` with a max-width. Never left-floated on a wide viewport.
3. **Full-bleed is media only** — video players and canvas elements can be full-width within their container. Text content never is.
4. **Section headings align with content** — if your content is inside a 1200px container, your section heading is too.
5. **Vertical rhythm before horizontal optimization** — establish the stacking order on mobile first. Horizontal layouts (side-by-side columns) are an enhancement for ≥768px.

---

## Key View Descriptions

These describe what each major view should feel and look like. Use these as the visual target when building or refactoring.

### Video List (Dashboard)

Open and spacious. A session log. Each card is an entry: thumbnail, title/date, serve count, status badge.

- Background: `--color-background`. Cards: white surface, `--color-border` border, `--radius-2xl` corners. **No shadow on cards.**
- The status badge is the only colored element per card. Green for complete, muted neutral for pending/processing.
- Card footer: action buttons separated by a `border-top` divider. Right-aligned. Maximum three actions per card. Edit button hovers use court-blue accent (not green — green is for primary actions only).
- Page header: video count (muted label), "Upload Video" button (green, primary, right side).
- The grid breathes. `--layout-card-gap` between cards.

### Analysis Dashboard

Focused and precise. Three-tier layout: breadcrumb header with view toggle, thumbnail strip for serve navigation, and a 70/30 two-column area (hero view left, metrics right).

- **Breadcrumb** trails "Library > filename.mp4 > Serve 3 of 8" — tells users exactly where they are. Page title "SERVE ANALYSIS" in uppercase.
- **View mode toggle** — a segmented pill with court-blue active state. "Video" shows the raw video; "Analysis" shows the stick-figure canvas with a PiP video in the corner.
- **Thumbnail strip** — horizontal scrollable row of video frame captures. Active serve has a court-blue border + subtle scale. Serve number badge + court side label below.
- **Court-line background** — subtle CSS grid pattern at 6% opacity gives the page a tennis-court texture.
- Metric values are the visual heroes of the sidebar. DM Mono, `--font-size-display-lg`, `--color-ink-heavy`. They dominate.
- Metric label sits below the value: DM Sans, `--font-size-xs`, uppercase, `--letter-spacing-wide`, `--color-text-muted`.
- **Annotations** (toss height brackets, laterality arrows, contact crosshairs) use rounded-rect label backdrops with the annotation palette. Visible in the stick-figure canvas.
- Color appears only in: the active phase indicator (green border/highlight), positive metric thresholds (green value), court-blue for navigation state, error states (error color).
- Both the main panel and sidebar are white surfaces with `--color-border` borders.

### Upload Flow

Narrow and focused. Max `--layout-narrow-max-width` (720px), centered.

- The dropzone is the visual anchor — the largest, most prominent element.
- Metadata form below: clean labels, standard spacing. One section at a time when possible.
- One primary button per step. No competing actions.

### Auth (Login / Signup)

Minimal. Centered card, max 440px. App name at top. Form below.

- Background: `--color-background`. No imagery, no gradients.
- The card has `--color-border` border and `--radius-3xl` corners.
- One primary action per view.

---

## What to Avoid

These are the patterns that produce generic-looking UI. Don't reach for them.

- **Gradient backgrounds** — not for standard UI. The landing page hero is the one exception.
- **Shadows on cards** — use border instead. Shadow signals elevation (modal, dropdown), not just distinction.
- **Green text** — the green accent is not a text color. Use the text hierarchy for text.
- **Center-aligned body text** — left-align body text. Center-align only short, isolated headlines (hero text, empty-state messages).
- **`translateY` hover lift on non-buttons** — subtle hover lift is for primary action buttons only. Cards and nav items should use border-color or background-color changes on hover instead.
- **Decorating empty states** — don't add large icons, illustrated backgrounds, or color blocks to empty states. Clean message, a clear action button. Done.
- **Competing visual hierarchies** — one primary visual element per section. If a card has a metric number, don't also give it a colored header band and a bold section title. Let the dominant element dominate.
- **Full-width text** — prose content wider than ~70ch is hard to read. Constrain text columns.
- **Mixing depth signals** — don't put a shadowed card inside another shadowed container. Depth levels nest; they don't stack.
