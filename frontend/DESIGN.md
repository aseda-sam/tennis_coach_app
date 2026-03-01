# Design System — CSS Patterns

CSS pattern reference for the Tennis Coach App. For aesthetic direction, color philosophy, and layout intent, see `VISUAL_IDENTITY.md`. All values come from `src/design-tokens.css`.

## Token Usage

Always use design tokens — never hardcode values.

```css
/* ✅ Good */
.button {
  padding: var(--button-padding-lg);
  background: var(--color-primary);
  border-radius: var(--button-border-radius);
  box-shadow: var(--shadow-primary-md);
  transition: var(--transition-normal);
}

/* ❌ Bad */
.button {
  padding: 14px 28px;
  background: #C8E86B;
  border-radius: 12px;
  box-shadow: 0 6px 14px rgba(200, 232, 107, 0.28);
  transition: all 0.2s ease;
}
```

## Component Patterns

### Buttons

```css
/* Primary — main actions ("Analyze", "Upload Video") */
.btn-primary {
  background: var(--color-primary);
  color: var(--color-court);   /* never white on Arc */
  border: none;
  padding: var(--button-padding-lg);
  border-radius: var(--button-border-radius);
  font-size: var(--font-size-lg);
  font-weight: var(--button-font-weight);
  cursor: pointer;
  transition: var(--transition-normal);
}
.btn-primary:hover {
  background: var(--color-primary-dark);
}

/* Secondary — less prominent actions */
.btn-secondary {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  padding: var(--button-padding-md);
  border-radius: var(--button-border-radius);
  font-size: var(--font-size-md);
  font-weight: var(--button-font-weight);
  cursor: pointer;
  transition: var(--transition-normal);
}
.btn-secondary:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-border-dark);
}

/* Icon-only */
.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
  color: var(--color-text-muted);
  padding: 0;
}
.btn-icon:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-border-dark);
  color: var(--color-text);
}
```

### Cards

```css
/* Standard */
.card {
  background: var(--color-surface);
  border-radius: var(--card-border-radius);
  border: 1px solid var(--color-border);
  padding: var(--card-padding);
  transition: var(--transition-normal);
}

/* Interactive (clickable) */
.card-interactive {
  background: var(--color-surface);
  border-radius: var(--card-border-radius);
  border: 1px solid var(--color-border);
  padding: var(--card-padding);
  cursor: pointer;
  transition: var(--transition-normal);
}
.card-interactive:hover {
  border-color: var(--color-border-dark);
}
```

### Inputs

```css
.input {
  width: 100%;
  padding: var(--input-padding);
  border: var(--input-border-width) solid var(--color-border);
  border-radius: var(--input-border-radius);
  font-size: var(--font-size-base);
  font-family: var(--font-family-sans);
  background: var(--color-surface);
  color: var(--color-text);
  transition: var(--transition-fast);
}
.input:focus {
  outline: var(--focus-outline-width) solid var(--focus-outline-color);
  outline-offset: var(--focus-outline-offset);
  border-color: var(--color-primary);
}
.input::placeholder {
  color: var(--color-text-disabled);
}
```

### Badges

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: 4px var(--spacing-md);
  border-radius: var(--radius-pill);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  white-space: nowrap;
}
.badge-success {
  background: var(--color-primary-soft);
  color: var(--color-arc-text);
  border: 1px solid var(--color-primary-light);
}
.badge-error {
  background: var(--color-error-soft);
  color: var(--color-error-dark);
  border: 1px solid var(--color-error-light);
}
.badge-muted {
  background: var(--color-surface-secondary);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
}
```

### Modals

```css
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: var(--color-modal-overlay);
  backdrop-filter: blur(4px);
  z-index: var(--z-modal-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal {
  background: var(--color-surface);
  border-radius: var(--radius-3xl);
  box-shadow: var(--shadow-3xl);
  padding: var(--spacing-4xl);
  max-width: 90vw;
  max-height: 90vh;
  overflow: auto;
  z-index: var(--z-modal);
  position: relative;
}
```

### Tooltips

CSS-only via `data-tooltip` attribute. No JS required.

```css
.controls [data-tooltip] {
  position: relative;
}
.controls [data-tooltip]::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%) translateY(4px);
  padding: 4px 10px;
  border-radius: var(--radius-md);
  background: var(--color-ink-heavy);
  color: white;
  font-family: var(--font-family-display);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition:
    opacity var(--duration-fast) var(--ease-in-out),
    transform var(--duration-fast) var(--ease-in-out);
  z-index: 20;
}
.controls [data-tooltip]:hover::after {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
  transition-delay: 0.4s;
}
.controls [data-tooltip]:disabled::after {
  display: none;
}
```

Rules: dark `--color-ink-heavy` background, white text, above the element, 400ms hover delay. Use `data-tooltip` not `title`. Keep labels short (2–3 words + optional keyboard shortcut).

## Depth System

**Borders for cards, panels, inputs** — `border: 1px solid var(--color-border)`. Cards are defined by their border, not shadow. This is what makes the UI look editorial rather than generic SaaS.

**Shadows for floating elements only** — modals, popovers, dropdowns, floating action buttons. Shadow signals *above the surface*, not just *distinct from it*.

- `--shadow-xs/sm`: sticky/header elements
- `--shadow-md/lg`: dropdowns, popovers
- `--shadow-xl/2xl/3xl`: modals, floating buttons
- `--shadow-primary-*`: primary action buttons only

Do not use shadows on cards or panels.

## Notes

- Dark mode: tokens are structured to support it; not yet implemented.
- Behavioral constraints (token enforcement, loading states, button hierarchy, accessibility) live in `.agents/rules/react-frontend.mdc`, not here.
