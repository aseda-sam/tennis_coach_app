# Diagrams (Mermaid Only)

Source-of-truth diagrams live here as Mermaid blocks in Markdown files.

## Conventions

- One diagram per file.
- Use a single Mermaid fence: ` ```mermaid ` ... ` ``` `.
- Prefer stable, high-level views over fast-changing details.

## Index

- `auth-flow.md` - Auth and session flow
- `upload-flow.md` - Upload, optional transcode, and scout/refine background pipeline
- `analysis-pipeline.md` - Transcode, scout/refine pose pipeline, serve windows, and analysis
- `data-flow.md` - End-to-end data movement
- `db-relationships.md` - Conceptual table relationships

## Validate

```bash
python .cursor/skills/diagram-maintainer/scripts/validate_mermaid.py
```

## Rendering in Cursor

If Mermaid isn't rendering, enable Markdown Mermaid preview in Cursor settings
(`markdown.preview.mermaid`) and open the Markdown preview (Cmd+Shift+V).
