# Diagrams (Mermaid Only)

Source-of-truth diagrams live here as Mermaid blocks in Markdown files.

## Conventions

- One diagram per file.
- Use a single Mermaid fence: ` ```mermaid ` ... ` ``` `.
- Prefer stable, high-level views over fast-changing details.

## Index

- **`system-overview.md`** - Full architecture in one diagram (context loader for AI sessions)
- `auth-flow.md` - Auth and session flow
- `upload-flow.md` - Upload, optional transcode, and scout/refine background pipeline
- `analysis-pipeline.md` - Transcode, scout/refine pose pipeline, serve windows, and analysis
- `data-flow.md` - End-to-end data movement
- `serve-feedback-pipeline.md` - Serve biomechanics pipeline (phases + raw metrics; no scoring)
- `db-relationships.md` - Conceptual table relationships

## Validate

```bash
python .agents/skills/diagram-maintainer/scripts/validate_mermaid.py
```

## Rendering

To preview Mermaid diagrams, use your editor's Markdown preview (most editors support Mermaid natively or via extensions). Open the Markdown preview with Cmd+Shift+V.
