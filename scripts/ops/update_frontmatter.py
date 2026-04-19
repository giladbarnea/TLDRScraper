#!/usr/bin/env python3
"""
Update last_updated frontmatter in markdown files.

Two modes:
  --scope=staged     : staged files (pre-commit). Timestamp only; re-stages each file.
  --scope=since-ref  : files modified in HEAD~1..HEAD (CI). Timestamp + commit hash.

Skip list is read from synced_external_subdirs.txt (column 3 = dest dir).

Doctests:
  >>> # tested via pytest / direct run of markdown_frontmatter.py
"""
import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import markdown_frontmatter

SKIP_FILES = {'PROJECT_STRUCTURE.md'}


def _read_synced_dirs() -> list[Path]:
    registry = Path(__file__).parent / 'synced_external_subdirs.txt'
    if not registry.exists():
        return []
    dirs = []
    for line in registry.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) >= 3:
            dirs.append(Path(parts[2]))
    return dirs


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _filter_md_files(raw_output: str, skip_dirs: list[Path]) -> list[Path]:
    files = []
    for line in raw_output.splitlines():
        if not line.endswith('.md'):
            continue
        f = Path(line)
        if f.name in SKIP_FILES or not f.exists():
            continue
        if any(f.is_relative_to(d) for d in skip_dirs):
            continue
        files.append(f)
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', required=True, choices=['staged', 'since-ref'])
    args = parser.parse_args()

    skip_dirs = _read_synced_dirs()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')

    if args.scope == 'staged':
        raw = _run(['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'])
        files = _filter_md_files(raw, skip_dirs)
        frontmatter = {'last_updated': now}
        def post_update(f: Path) -> None:
            subprocess.run(['git', 'add', str(f)], check=True)
    else:
        raw = _run(['git', 'diff', '--name-only', '--diff-filter=AM', 'HEAD~1', 'HEAD'])
        files = _filter_md_files(raw, skip_dirs)
        commit_hash = _run(['git', 'rev-parse', '--short=7', 'HEAD'])
        frontmatter = {'last_updated': f'{now}, {commit_hash}'}
        def post_update(f: Path) -> None:
            pass  # CI handles git add '*.md' in the next step

    if not files:
        print('No markdown files to update.')
        return 0

    print(f'Updating {len(files)} file(s): {frontmatter["last_updated"]}')
    for f in files:
        markdown_frontmatter.update(f, frontmatter)
        post_update(f)
        print(f'  ✓ {f}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
