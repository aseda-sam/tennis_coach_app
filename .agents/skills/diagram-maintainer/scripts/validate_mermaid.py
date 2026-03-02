#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

START_FENCE = "```mermaid"
END_FENCE = "```"


def repo_root() -> Path:
    # scripts/ -> diagram-maintainer/ -> skills/ -> .agents/ -> repo/
    return Path(__file__).resolve().parents[4]


def find_diagram_files(diagrams_dir: Path) -> list[Path]:
    return sorted(
        [
            *diagrams_dir.rglob("*.md"),
            *diagrams_dir.rglob("*.mmd"),
        ]
    )


def validate_file(path: Path) -> list[str]:
    if path.name.lower() == "readme.md":
        return []

    errors: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    in_mermaid = False
    block_line = None
    has_block = False

    for idx, line in enumerate(lines, start=1):
        if line.strip() == START_FENCE:
            if in_mermaid:
                errors.append(
                    f"{path}: line {idx} starts a Mermaid block before closing the previous one"
                )
            in_mermaid = True
            has_block = True
            block_line = idx
            continue

        if line.strip() == END_FENCE and in_mermaid:
            in_mermaid = False
            block_line = None
            continue

    if in_mermaid:
        errors.append(
            f"{path}: Mermaid block opened at line {block_line} is not closed"
        )

    if not has_block:
        errors.append(f"{path}: no Mermaid block found")

    return errors


def main() -> int:
    root = repo_root()
    diagrams_dir = root / "docs" / "diagrams"

    if not diagrams_dir.exists():
        print(f"Missing diagrams directory: {diagrams_dir}")
        return 1

    files = find_diagram_files(diagrams_dir)
    if not files:
        print(f"No diagram files found in {diagrams_dir}")
        return 1

    errors: list[str] = []
    for path in files:
        errors.extend(validate_file(path))

    if errors:
        print("Mermaid validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Mermaid validation passed ({len(files)} file(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
