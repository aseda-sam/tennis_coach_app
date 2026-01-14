# Design System

This document outlines the design system and component patterns used throughout the Tennis Coach App frontend.

## Philosophy

**Consistency is key.** This design system provides a foundation for building consistent, maintainable UI components without heavy framework dependencies.

## Design Tokens

All design tokens are defined in `src/design-tokens.css`. Import this file in your main CSS entry point.

### Usage

```css
/* ✅ Good - Use design tokens */
.button {
  padding: var(--spacing-md) var(--spacing-2xl);
  background: var(--color-primary);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-primary-md);
  transition: var(--transition-normal);
}

/* ❌ Bad - Hardcoded values */
.button {
  padding: 12px 24px;
  background: #00bc7d;
  border-radius: 12px;
  box-shadow: 0 6px 14px rgba(0, 188, 125, 0.28);
  transition: all 0.2s ease;
}
```

## Component Patterns

### Buttons

#### Primary Button
Used for main actions (e.g., "Upload Video", "Start Analysis").

```css
.btn-primary {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: white;
  border: none;
  padding: var(--button-padding-lg);
  border-radius: var(--button-border-radius);
  font-size: var(--font-size-lg);
  font-weight: var(--button-font-weight);
  cursor: pointer;
  transition: var(--transition-normal);
  box-shadow: var(--shadow-primary-lg);
}

.btn-primary:hover {
  background: linear-gradient(135deg, var(--color-primary-dark) 0%, var(--color-primary-darker) 100%);
  transform: translateY(-2px);
  box-shadow: var(--shadow-primary-xl);
}
```

#### Secondary Button
Used for less prominent actions.

```css
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
  box-shadow: var(--shadow-sm);
}

.btn-secondary:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-border-dark);
  box-shadow: var(--shadow-md);
}
```

#### Icon Button
For icon-only actions.

```css
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

#### Standard Card
Used for displaying content blocks (e.g., video cards, analysis results).

```css
.card {
  background: var(--color-surface);
  border-radius: var(--card-border-radius);
  box-shadow: var(--card-shadow);
  border: 1px solid var(--color-border-light);
  padding: var(--card-padding);
  transition: var(--transition-normal);
}

.card:hover {
  box-shadow: var(--card-shadow-hover);
  transform: translateY(-1px);
}
```

#### Interactive Card
For clickable cards (e.g., video list items).

```css
.card-interactive {
  background: var(--color-surface);
  border-radius: var(--card-border-radius);
  box-shadow: var(--card-shadow);
  border: 1px solid var(--color-overlay-light);
  padding: var(--card-padding);
  cursor: pointer;
  transition: var(--transition-normal);
}

.card-interactive:hover {
  box-shadow: var(--card-shadow-hover);
  transform: translateY(-1px);
  border-color: var(--color-border);
}
```

### Inputs

#### Text Input
Standard text input fields.

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

### Badges & Pills

#### Status Badge
For displaying status indicators (e.g., analysis status, video count).

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
  color: var(--color-success-dark);
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

#### Modal Container
For overlay dialogs and modals.

```css
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.5);
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

## Spacing Guidelines

Use the spacing scale consistently:

- **xs (4px)**: Tight spacing between related elements (icon + text)
- **sm (8px)**: Small gaps (button groups, list items)
- **md (12px)**: Default spacing (form fields, card padding)
- **lg (16px)**: Standard spacing (sections, margins)
- **xl (20px)**: Container padding
- **2xl (24px)**: Card padding, section spacing
- **3xl+**: Large spacing (page sections, major dividers)

## Typography Guidelines

### Headings
- **Page Title**: `font-size: var(--font-size-5xl)`, `font-weight: var(--font-weight-bold)`
- **Section Title**: `font-size: var(--font-size-4xl)`, `font-weight: var(--font-weight-semibold)`
- **Card Title**: `font-size: var(--font-size-md)`, `font-weight: var(--font-weight-semibold)`

### Body Text
- **Default**: `font-size: var(--font-size-base)`, `line-height: var(--line-height-relaxed)`
- **Muted**: `color: var(--color-text-muted)`, `font-size: var(--font-size-sm)`
- **Small**: `font-size: var(--font-size-xs)` (labels, captions)

## Color Usage

### Primary Actions
Use `--color-primary` for primary actions, links, and highlights.

### Text Hierarchy
- **Primary Text**: `--color-text` (headings, important content)
- **Secondary Text**: `--color-text-secondary` (body text)
- **Muted Text**: `--color-text-muted` (metadata, labels)
- **Disabled Text**: `--color-text-disabled` (inactive elements)

### Surfaces
- **Surface**: `--color-surface` (cards, modals, inputs)
- **Surface Secondary**: `--color-surface-secondary` (alternating backgrounds)
- **Background**: `--color-background` (page background)

## Shadows

Use shadows to create depth hierarchy:

- **xs/sm**: Subtle elevation (inputs, small cards)
- **md**: Standard elevation (buttons, cards)
- **lg/xl**: Prominent elevation (modals, hover states)
- **Primary shadows**: For primary action buttons

## Transitions

Use consistent transitions for interactive elements:

- **Fast (0.15s)**: Hover states, quick feedback
- **Normal (0.2s)**: Standard interactions (buttons, cards)
- **Slow (0.25s)**: Complex animations, transforms

Always use `var(--ease-in-out)` for smooth, natural motion.

## Accessibility

### Focus States
All interactive elements must have visible focus states:

```css
.element:focus {
  outline: var(--focus-outline-width) solid var(--focus-outline-color);
  outline-offset: var(--focus-outline-offset);
}
```

### Reduced Motion
The design system automatically respects `prefers-reduced-motion`. Transitions are minimized for users who prefer reduced motion.

### Color Contrast
Ensure sufficient contrast:
- Text on surfaces: Minimum 4.5:1 ratio
- Interactive elements: Minimum 3:1 ratio

## Responsive Design

Use breakpoints defined in design tokens:

- **sm**: 640px
- **md**: 768px (tablets)
- **lg**: 1024px (small desktops)
- **xl**: 1280px (desktops)

Example:

```css
.card {
  padding: var(--spacing-lg);
}

@media (min-width: 768px) {
  .card {
    padding: var(--spacing-2xl);
  }
}
```

## Best Practices

1. **Always use design tokens** - Never hardcode colors, spacing, or other values
2. **Follow component patterns** - Use established patterns for consistency
3. **Maintain hierarchy** - Use typography and spacing to create clear visual hierarchy
4. **Test accessibility** - Ensure focus states and contrast meet WCAG guidelines
5. **Keep it simple** - Don't over-engineer; use the simplest solution that works

## Migration Guide

When updating existing components:

1. Replace hardcoded colors with `var(--color-*)` tokens
2. Replace hardcoded spacing with `var(--spacing-*)` tokens
3. Replace hardcoded shadows with `var(--shadow-*)` tokens
4. Replace hardcoded transitions with `var(--transition-*)` tokens
5. Update border-radius values to use `var(--radius-*)` tokens

Example migration:

```css
/* Before */
.button {
  padding: 12px 24px;
  background: #00bc7d;
  border-radius: 12px;
  box-shadow: 0 6px 14px rgba(0, 188, 125, 0.28);
  transition: all 0.2s ease;
}

/* After */
.button {
  padding: var(--button-padding-md);
  background: var(--color-primary);
  border-radius: var(--button-border-radius);
  box-shadow: var(--shadow-primary-md);
  transition: var(--transition-normal);
}
```

## Future Enhancements

- Dark mode support (tokens ready, implementation pending)
- Additional component patterns as needed
- Icon system documentation (when lucide-react is added)
