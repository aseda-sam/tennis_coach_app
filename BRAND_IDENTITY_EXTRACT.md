# Brand & Visual Identity Extract — Second Serve

> Extracted from: `frontend/VISUAL_IDENTITY.md`, `frontend/DESIGN.md`, `frontend/src/design-tokens.css`, `.agents/rules/frontend-design.mdc`, `.agents/rules/react-frontend.mdc`, `AGENTS.md`, and component CSS files.

---

## 1. Brand Basics

- **Working name:** "Second Serve" (in testing — repo still uses "Tennis Coach App")
- **What it is:** A serve-analysis MVP. Users upload serve videos, the app runs pose estimation, tags serve windows, segments phases, and returns metrics.
- **Positioning:** A coach-prep tool. Helps users identify what to work on, gives language to use with a coach, encourages practice. Complements coaches — doesn't replace them.
- **Logo mark:** 36×36px rounded square (`border-radius: 10px`), filled `#0a0f1a` (ink-heavy), with a white icon inside. Scales up on hover.

---

## 2. Aesthetic Direction: "Richer Clean Sport"

Light, confident, editorial — with tennis personality. Think of a well-designed sports magazine spread: generous margins, strong typography, content given room to breathe.

**Key qualities:**
- **Light everywhere.** White surfaces, near-white backgrounds. Darkness is reserved for text and display numbers.
- **Space signals importance.** Generous margins and padding. Cramped UI feels cheap.
- **Typography carries the personality.** The fonts do the design work — not gradients, not color blocks, not decorative elements.
- **Green is earned.** Reserved for action and positive state only. Not headers, not backgrounds, not decoration.
- **Court blue adds wayfinding.** Active states, breadcrumb hovers, thumbnail highlights. Signals "you are here" and "this is tennis."
- **Court-line patterns add texture.** Subtle CSS grid lines at very low opacity (6–7%) whisper "court" without competing.
- **Numbers are the heroes.** Metric values dominate visually in the analysis view.
- **Annotations are first-class.** Toss height brackets, laterality arrows, contact crosshairs are designed to be beautiful.
- **Borders define depth, not shadows.** Cards are defined by `1px solid` borders, not box-shadows. Shadows are reserved for modals, popovers, and floating elements only.

---

## 3. Color Palette

### Primary Green
| Token | Hex | Purpose |
|-------|-----|---------|
| `--color-primary` | `#00bc7d` | **Primary action & positive state.** Primary buttons ("Analyze", "Save"), completed badges, positive highlights. |
| `--color-primary-dark` | `#009966` | Hover state for primary buttons |
| `--color-primary-darker` | `#007a55` | Pressed/active state |
| `--color-primary-light` | `#33c99a` | Badge borders |
| `--color-primary-lighter` | `#66d6b7` | Light accent |
| `--color-primary-soft` | `#ecfdf5` | Soft background for success/completed states |
| `--color-primary-softest` | `#f0fdf7` | Lightest green tint |

**Usage rule:** Green is scarce by design. If you're using green for brand identity, decoration, or a non-primary-action button — stop. The scarcity is what makes it work.

### Court Blue
| Token | Hex | Purpose |
|-------|-----|---------|
| `--color-court-blue` | `#1b4b7a` | **Spatial identity & wayfinding.** Active toggle segments, nav active states, breadcrumb hovers, active thumbnail borders, scrubber accents, edit-button hover accents. |
| `--color-court-blue-light` | `#2a6cb0` | Lighter wayfinding accent |
| `--color-court-blue-soft` | `rgba(27, 75, 122, 0.08)` | Hover backgrounds |

**Usage rule:** Says "tennis court" without being literal. For navigation and "you are here" moments.

### Amber Gold
| Token | Hex | Purpose |
|-------|-----|---------|
| `--color-amber` | `#c8941a` | **Second accent for non-action highlights.** Active nav tab state, interesting data moments, status indicators that aren't success/error. |
| `--color-amber-dark` | `#a97a14` | Darker amber variant |
| `--color-amber-soft` | `rgba(200, 148, 26, 0.1)` | Amber hover/badge backgrounds |
| `--color-amber-softest` | `rgba(200, 148, 26, 0.07)` | Feature icon badge backgrounds |

**Usage rule:** "This is noteworthy but not a call to action." Not for primary buttons.

### Court-Inspired (Reserved)
| Token | Hex | Purpose |
|-------|-----|---------|
| `--color-court-clay` | `#d4784a` | Reserved for future court-surface theming |
| `--color-court-clay-soft` | `rgba(212, 120, 74, 0.1)` | Reserved |
| `--color-ball-yellow` | `#ccff00` | Reserved for ball-tracking highlights |
| `--color-ball-yellow-soft` | `rgba(204, 255, 0, 0.12)` | Reserved |

### Annotation Palette (Canvas Overlays)
| Token | Hex | Purpose |
|-------|-----|---------|
| `--color-annotation-primary` | `#00d4ff` | Cyan — lines, brackets, labels, contact crosshair |
| `--color-annotation-accent` | `#ff1493` | Magenta — ball trail, head dot |
| `--color-annotation-skeleton` | `#4ad090` | Desaturated analytical green — skeleton bones, joints |
| `--color-ground-reference` | `#6b7a8d` | Neutral cool blue-grey — ground plane line |

### Neutral / Text
| Token | Hex | Purpose |
|-------|-----|---------|
| `--color-ink-heavy` | `#0a0f1a` | Near-black. Large metric numbers, hero headings. Visual authority. Not for body text. |
| `--color-text` | `#101828` | Primary body text, card content, standard UI |
| `--color-text-secondary` | `#374151` | Secondary body text |
| `--color-text-muted` | `#4a5565` | Metadata, timestamps, metric labels |
| `--color-text-disabled` | `#9ca3af` | Inactive elements |

### Surfaces & Backgrounds
| Token | Hex | Purpose |
|-------|-----|---------|
| `--color-background` | `#f8f5f1` | **Warm parchment.** Page canvas. Slightly warm so white cards read as surfaces without shadows. Never use cold blue-tinted backgrounds. |
| `--color-background-alt` | `#f4f0eb` | Alternate background |
| `--color-surface` | `#ffffff` | Cards, panels, modals. Crisp white. |
| `--color-surface-secondary` | `#f4f0eb` | Alternating backgrounds |
| `--color-surface-tertiary` | `#edeae5` | Third-level surfaces |
| `--color-surface-hover` | `#f5f2ee` | Hover state for surfaces |
| `--color-sand` | `#f5f0e8` | Warm neutral for milestone/highlight sections. Sparingly — one per page max. |
| `--color-sand-dark` | `#ede8de` | Border on sand backgrounds |

### Borders
| Token | Hex | Purpose |
|-------|-----|---------|
| `--color-border` | `#e5e7eb` | Primary depth tool. Cards and dividers. |
| `--color-border-light` | `#f3f4f6` | Light dividers |
| `--color-border-dark` | `#d1d5db` | Hover state borders |

### Semantic Colors
| Token | Hex |
|-------|-----|
| Success: `--color-success` | `#10b981` |
| Success Light: `--color-success-light` | `#d1fae5` |
| Success Dark: `--color-success-dark` | `#059669` |
| Error: `--color-error` | `#dc2626` |
| Error Light: `--color-error-light` | `#fee2e2` |
| Error Dark: `--color-error-dark` | `#b91c1c` |
| Warning: `--color-warning` | `#f59e0b` |
| Warning Light: `--color-warning-light` | `#fef3c7` |
| Warning Dark: `--color-warning-dark` | `#d97706` |
| Info: `--color-info` | `#3b82f6` |
| Info Light: `--color-info-light` | `#dbeafe` |
| Info Dark: `--color-info-dark` | `#1e40af` |

### Overlays
| Token | Value |
|-------|-------|
| `--color-overlay` | `rgba(15, 23, 42, 0.08)` |
| `--color-overlay-dark` | `rgba(15, 23, 42, 0.12)` |
| `--color-overlay-glass` | `rgba(255, 255, 255, 0.8)` |
| `--color-modal-overlay` | `rgba(15, 23, 42, 0.5)` |

---

## 4. Typography

### Font Families
| Role | Font | Weights | Why |
|------|------|---------|-----|
| **UI / Body** | DM Sans | 300, 400, 500, 600, 700 | Slightly rounded geometry — sporty & approachable. More character than Inter at display sizes. |
| **Metric display** | DM Mono | 400, 500 | Numbers deserve monospaced for consistent width and visual precision. Reads as "precise measurement" not "developer terminal." |

**Font stacks:**
- Sans: `'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif`
- Mono: `'DM Mono', source-code-pro, Menlo, Monaco, Consolas, 'Courier New', monospace`

### Type Scale
| Level | Token | Size | Weight | Font | Use |
|-------|-------|------|--------|------|-----|
| Hero metric | `--font-size-display-xl` | 3rem (48px) | 500 | DM Mono | Single standout number |
| Large metric | `--font-size-display-lg` | 2.5rem (40px) | 500 | DM Mono | Primary metric values |
| Medium metric | `--font-size-display-md` | 2rem (32px) | 500 | DM Mono | Secondary metric values |
| Small metric | `--font-size-display-sm` | 1.5rem (24px) | 500 | DM Mono | Compact metrics, timeline annotations |
| Page heading | `--font-size-5xl` | 1.6rem (25.6px) | 700 | DM Sans | Page titles (h1) |
| Section heading | `--font-size-4xl` | 1.25rem (20px) | 600 | DM Sans | Section/panel headers (h2) |
| Card title | `--font-size-xl` | 1rem (16px) | 600 | DM Sans | Card headers, group labels |
| Body | `--font-size-base` | 0.875rem (14px) | 400 | DM Sans | Body text, descriptions |
| Label | `--font-size-sm` | 0.8rem (12.8px) | 500 | DM Sans | Field labels, metric labels |
| Caption | `--font-size-xs` | 0.75rem (12px) | 400 | DM Sans | Timestamps, fine print |

### Full Size Scale
| Token | Size |
|-------|------|
| `--font-size-xs` | 0.75rem (12px) |
| `--font-size-sm` | 0.8rem (12.8px) |
| `--font-size-base` | 0.875rem (14px) |
| `--font-size-md` | 0.9rem (14.4px) |
| `--font-size-lg` | 0.95rem (15.2px) |
| `--font-size-xl` | 1rem (16px) |
| `--font-size-2xl` | 1.05rem (16.8px) |
| `--font-size-3xl` | 1.1rem (17.6px) |
| `--font-size-4xl` | 1.25rem (20px) |
| `--font-size-5xl` | 1.6rem (25.6px) |
| `--font-size-6xl` | 2rem (32px) |

### Font Weights
| Token | Value |
|-------|-------|
| `--font-weight-normal` | 400 |
| `--font-weight-medium` | 500 |
| `--font-weight-semibold` | 600 |
| `--font-weight-bold` | 700 |
| `--font-weight-extrabold` | 800 |

### Line Heights
| Token | Value |
|-------|-------|
| `--line-height-tight` | 1.2 |
| `--line-height-normal` | 1.4 |
| `--line-height-relaxed` | 1.6 |
| `--line-height-loose` | 1.7 |
| `--line-height-extra-loose` | 1.8 |

### Letter Spacing
| Token | Value |
|-------|-------|
| `--letter-spacing-tight` | -0.025em |
| `--letter-spacing-normal` | -0.02em |
| `--letter-spacing-relaxed` | -0.01em |
| `--letter-spacing-wide` | 0.01em |

### Metric Label Pattern
Always uppercase, wide letter-spacing, muted color:
```
2.4 s             ← DM Mono, display-md, --color-ink-heavy
CONTACT TIME      ← DM Sans, xs, uppercase, letter-spacing-wide, --color-text-muted
```

---

## 5. Spacing Scale

| Token | Value |
|-------|-------|
| `--spacing-xs` | 4px |
| `--spacing-sm` | 8px |
| `--spacing-md` | 12px |
| `--spacing-lg` | 16px |
| `--spacing-xl` | 20px |
| `--spacing-2xl` | 24px |
| `--spacing-3xl` | 28px |
| `--spacing-4xl` | 32px |
| `--spacing-5xl` | 40px |
| `--spacing-6xl` | 48px |
| `--spacing-7xl` | 52px |
| `--spacing-8xl` | 60px |
| `--spacing-9xl` | 80px |

### Usage Guidelines
- **xs (4px):** Tight spacing between related elements (icon + text)
- **sm (8px):** Small gaps (button groups, list items)
- **md (12px):** Default spacing (form fields, card padding)
- **lg (16px):** Standard spacing (sections, margins)
- **xl (20px):** Container padding
- **2xl (24px):** Card padding, section spacing
- **3xl+:** Large spacing (page sections, major dividers)

---

## 6. Border Radius Scale

| Token | Value |
|-------|-------|
| `--radius-xs` | 4px |
| `--radius-sm` | 6px |
| `--radius-md` | 8px |
| `--radius-lg` | 10px |
| `--radius-xl` | 12px |
| `--radius-2xl` | 14px |
| `--radius-3xl` | 16px |
| `--radius-full` | 9999px |
| `--radius-pill` | 20px |

---

## 7. Shadow System

### Neutral Shadows
| Token | Value |
|-------|-------|
| `--shadow-xs` | `0 1px 2px 0 rgba(0, 0, 0, 0.05)` |
| `--shadow-sm` | `0 1px 2px rgba(15, 23, 42, 0.06), 0 1px 3px rgba(15, 23, 42, 0.08)` |
| `--shadow-md` | `0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)` |
| `--shadow-lg` | `0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)` |
| `--shadow-xl` | `0 12px 24px rgba(15, 23, 42, 0.08)` |
| `--shadow-2xl` | `0 16px 28px rgba(15, 23, 42, 0.12)` |
| `--shadow-3xl` | `0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)` |

### Primary (Green) Shadows — for primary action buttons only
| Token | Value |
|-------|-------|
| `--shadow-primary-sm` | `0 1px 2px rgba(0, 0, 0, 0.04)` |
| `--shadow-primary-md` | `0 6px 14px rgba(0, 188, 125, 0.28)` |
| `--shadow-primary-lg` | `0 8px 16px rgba(0, 188, 125, 0.25)` |
| `--shadow-primary-xl` | `0 10px 18px rgba(0, 188, 125, 0.38)` |
| `--shadow-primary-2xl` | `0 12px 20px rgba(0, 188, 125, 0.3)` |

### Depth Philosophy
- **Borders for:** cards, panels, inputs, form fields, dividers. `1px solid --color-border`.
- **Shadows for:** modals, popovers, dropdown menus, floating action buttons only.
- Cards defined by border have more editorial clarity than cards with heavy box-shadows.

---

## 8. Layout Grammar

### Container Widths
| Context | Token | Value |
|---------|-------|-------|
| Standard content | `--layout-content-max-width` | 1200px |
| Narrow / focused | `--layout-narrow-max-width` | 720px |
| Full page bound | `--layout-page-max-width` | 1440px |
| Auth forms | `--layout-auth-max-width` | 420px |

### Responsive Gutter
`--layout-page-gutter: clamp(16px, 4vw, 48px)` — scales with viewport, no breakpoint logic needed.

### Spacing Rhythm
| Context | Token | Value |
|---------|-------|-------|
| Between major page sections | `--layout-section-gap` | 80px |
| Between cards in a grid | `--layout-card-gap` | 24px |
| Card grid column minimum | `--layout-card-grid-min` | 280px |

### Header
- Height: `--app-header-height: 56px`
- Sticky, frosted glass: `background: rgba(248, 245, 241, 0.97)` with `backdrop-filter: blur(20px)`
- Bottom border: `--color-sand-dark`
- Max content width: 1200px, centered

### Standard Patterns
```css
/* Standard page container */
.page-container {
  max-width: var(--layout-content-max-width); /* 1200px */
  margin: 0 auto;
  padding: 0 var(--layout-page-gutter);
}

/* Standard card grid */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--layout-card-gap); /* 24px */
}
```

### Page Structure Rules
1. Every page has a page header — title (h1), optional subtitle, optional primary CTA. Inside the container.
2. Content columns always centered — `margin: 0 auto` with max-width.
3. Full-bleed is media only — video players and canvas can be full-width. Text never.
4. Section headings align with content.
5. Vertical rhythm before horizontal optimization — mobile-first stacking.

### Breakpoints
| Name | Value |
|------|-------|
| sm | 640px |
| md | 768px |
| lg | 1024px |
| xl | 1280px |
| 2xl | 1536px |

---

## 9. Motion & Transitions

### Timing Functions
| Token | Value |
|-------|-------|
| `--ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` |
| `--ease-out` | `cubic-bezier(0, 0, 0.2, 1)` |
| `--ease-in` | `cubic-bezier(0.4, 0, 1, 1)` |

### Durations
| Token | Value | Use |
|-------|-------|-----|
| `--duration-fast` | 0.15s | Hover states, quick feedback |
| `--duration-normal` | 0.2s | Standard interactions |
| `--duration-slow` | 0.25s | Complex animations, transforms |
| `--duration-slower` | 0.3s | Modal entrances |

### Standard Transitions
```css
--transition-fast: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
--transition-normal: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
--transition-slow: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
--transition-slower: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
```

### Modal Entrance Animation
```css
@keyframes modalSlideIn {
  from { opacity: 0; transform: translateY(-20px) scale(0.95); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
```

### Rules
- Meaningful transitions only: state changes, visibility changes, navigation transitions. No decorative animation.
- Respects `prefers-reduced-motion` — all durations reduce to 0.01ms.
- CSS transitions preferred over JS animation.

---

## 10. Z-Index Scale

| Token | Value | Use |
|-------|-------|-----|
| `--z-base` | 0 | Default |
| `--z-dropdown` | 1000 | Dropdowns |
| `--z-sticky` | 1000 | Sticky header |
| `--z-fixed` | 1000 | Fixed elements |
| `--z-modal-backdrop` | 2000 | Modal overlay |
| `--z-modal` | 2100 | Modal content |
| `--z-popover` | 2200 | Popovers |
| `--z-tooltip` | 2300 | Tooltips |

---

## 11. Component Patterns

### Buttons
- **Primary:** Green (`--color-primary`), white text, `--radius-xl` (12px), green shadow. Hover: darker green + elevated shadow. `translateY(-1px)` on hover for subtle lift.
- **Secondary/Neutral CTA:** Ink-heavy (`#0a0f1a`) background or white with border. Not green.
- **Icon buttons:** 32×32px, `--color-border` border, `--radius-sm`, muted color → darker on hover.
- **Destructive:** Error color on hover, soft red background.
- **Minimum touch target:** 36px height.
- **Pill buttons:** `--radius-pill` (20px) for CTA-style buttons.

### Cards
- White surface, `1px solid --color-border`, `--radius-2xl` (14px), **no shadow**.
- Card padding: 24px (`--card-padding`).
- Card actions at bottom separated by `border-top`, right-aligned, max 3 actions.
- Edit button hover: court-blue accent (not green).

### Inputs
- Padding: 12px 16px, `--radius-md` (8px) border, 1px border.
- Focus: border turns `--color-primary`, optional outline ring.
- Custom select dropdowns: `appearance: none` + custom SVG chevron, neutral gray arrow.

### Badges / Pills
- Pill radius: `--radius-pill` (20px) or `--radius-full`.
- Uppercase, letter-spacing wide, semibold, xs font.
- Success: soft green bg + dark green text. Error: soft red bg + dark red text. Muted: secondary bg + muted text.

### Modals
- Centered, `--radius-3xl` (16px), `--shadow-3xl`.
- Backdrop: `rgba(15, 23, 42, 0.5)` + `backdrop-filter: blur(4–5px)`.
- Entrance: slide-in animation (0.3s, ease-out).
- Max width 900px, 90% viewport width.

### Loading States
- Spinner ring: border-top is `--color-primary`, rest is `--color-border-light`.
- Three sizes: sm (22px), md (34px), lg (46px).
- Always include user-facing loading text in warm, present-continuous voice.
- Loading copy tone: "Watching your serve..." not "Video is being processed..."

### Glass Effect
```css
.glass {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}
```

### Text Selection
```css
::selection {
  background: var(--color-info-light); /* #dbeafe */
  color: var(--color-info-dark);       /* #1e40af */
}
```

### Scrollbar
- Width: 8px. Track: `--color-surface-tertiary`. Thumb: `--color-border-dark`, `--radius-xs`.

---

## 12. Court-Line Texture Pattern

A signature visual element — CSS grid lines at ~7% opacity that give the background a tennis-court feel:

```css
.court-pattern {
  background-image:
    repeating-linear-gradient(0deg,
      rgba(160, 120, 80, 0.07) 0, rgba(160, 120, 80, 0.07) 1px,
      transparent 1px, transparent 48px),
    repeating-linear-gradient(90deg,
      rgba(160, 120, 80, 0.07) 0, rgba(160, 120, 80, 0.07) 1px,
      transparent 1px, transparent 48px);
}
```

Variants: `--vertical` (vertical lines only) and `--horizontal` (horizontal lines only). Used on analysis page backgrounds and stick-figure canvas.

---

## 13. Icon Badge Pattern

Standard pattern for feature/category icon containers:
```css
--icon-badge-bg: rgba(200, 148, 26, 0.07);    /* amber-softest */
--icon-badge-border: rgba(200, 148, 26, 0.1);  /* amber-soft */
--icon-badge-color: #c8941a;                    /* amber */
--icon-badge-size: 36px;
--icon-badge-radius: 8px;
```

---

## 14. Key View Descriptions

### Video List (Dashboard)
Open, spacious session log. White cards with border (no shadow), `--radius-xl`. Auto-fill grid with 280px minimum. Status badge is the only color per card. Page header has video count + "Upload Video" button. Upload button uses ink-heavy (`#0a0f1a`), not green.

### Analysis Dashboard
Focused and precise. Three tiers: breadcrumb header with view toggle → thumbnail strip → 70/30 two-column (hero view left, metrics right). Max width 1440px.

- **Breadcrumb:** "Library > filename.mp4 > Serve 3 of 8"
- **View toggle:** Segmented pill, court-blue active state
- **Thumbnail strip:** Horizontal scroll, court-blue active border + subtle scale
- **Scrubber:** Court-blue thumb and active phase segments
- **Metric values:** DM Mono, display-lg (40px), ink-heavy color
- **Court-line background** at 6% opacity

### Upload Flow
Narrow (720px max), centered. Dropzone is the visual anchor. One primary button per step.

### Auth (Login / Signup)
Minimal centered card, max 420px. Warm parchment background. `--radius-2xl` corners. One primary action per view. No imagery or gradients.

### Demo Landing Page
Hero section with display-xl title (3rem). Primary CTA card uses solid green background with white text and white button. Subtle radial gradient glow at top. 4-column feature grid with amber icon badges. Footer strip with feedback links.

---

## 15. UI Copy & Voice

- **Title Case** for buttons, headings, nav labels, prominent UI text ("Find Serve Windows", "Re-Analyze Serves").
- **Sentence case** only for body/helper text and toasts.
- **No coaching language in UI.** Use "metrics", "analysis", "your serve data" — not "your coach recommends" or "we suggest." Frame as data, not instruction.
- **Loading states:** Brief, warm, human. Present-continuous ("Watching your serve..."), not passive ("Video is being processed..."). No puns or emojis.

---

## 16. Design Anti-Patterns (What to Avoid)

- **Gradient backgrounds** — not for standard UI (landing hero is the one exception)
- **Shadows on cards** — use border instead
- **Green text** — green is not a text color
- **Center-aligned body text** — left-align. Center only for short isolated headlines.
- **`translateY` hover on non-buttons** — hover lift for primary buttons only
- **Decorating empty states** — clean message + action button only
- **Competing visual hierarchies** — one primary element per section
- **Full-width text** — constrain to ~70ch
- **Mixing depth signals** — no shadow inside shadow
- **Cold blue-tinted backgrounds** — use warm parchment tones
- **Heavy icon/illustration empty states** — minimalist approach

---

## 17. Accessibility

- Focus states required on all interactive elements: `2px solid --color-primary`, `2px offset`.
- Reduced motion: all durations collapse to 0.01ms via `prefers-reduced-motion: reduce`.
- Color contrast: 4.5:1 minimum for text, 3:1 for interactive elements.
- Loading indicators: `role="status"`, `aria-live="polite"`.
- Required fields: red asterisk with `aria-label="required"`.

---

## 18. Dark Mode Status

Not yet implemented. Token structure is ready for it. CSS custom properties make the switch straightforward.
