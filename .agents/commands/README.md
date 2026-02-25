# Commands

Tool-agnostic command intents for this repository.

Purpose:
- Keep reusable command workflows in one shared place (`.agents/commands/`).
- Avoid relying on tool-specific command folders as the canonical source.

Usage model:
- The user can invoke a command intent in natural language (for example: "ship it").
- Agents should map the user phrase to the closest command file in this folder.

Local adapters:
- Tool-specific command systems (Cursor, Claude Code, others) can mirror or symlink to this folder locally.
- Keep those adapters local/ignored when they contain personal workflows.
