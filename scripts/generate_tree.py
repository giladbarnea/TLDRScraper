#!/usr/bin/env python3
"""
Generate a directory tree structure similar to 'eza --tree'.
Drop-in replacement for eza to avoid installation time.

Usage:
    python generate_tree.py [--all] [--git-ignore] [--ignore-glob PATTERNS] [PATH]
"""

import os
import sys
import fnmatch
import argparse
from pathlib import Path
from typing import Set, List, Optional


def parse_gitignore(gitignore_path: Path) -> List[str]:
    """
    Parse .gitignore file and return list of patterns.

    >>> patterns = parse_gitignore(Path('.gitignore'))
    >>> '__pycache__' in patterns or '__pycache__/' in patterns
    True
    """
    if not gitignore_path.exists():
        return []

    patterns = []
    with open(gitignore_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                patterns.append(line)
    return patterns


def should_ignore(path: Path, base_dir: Path, gitignore_patterns: List[str],
                  extra_patterns: List[str], show_hidden: bool) -> bool:
    """
    Check if a path should be ignored based on gitignore and extra patterns.

    >>> should_ignore(Path('node_modules/foo'), Path('.'), ['node_modules'], [], True)
    True
    >>> should_ignore(Path('.hidden'), Path('.'), [], [], False)
    True
    >>> should_ignore(Path('.hidden'), Path('.'), [], [], True)
    False
    """
    rel_path = path.relative_to(base_dir)
    rel_path_str = str(rel_path)
    name = path.name

    if not show_hidden and name.startswith('.') and name not in {'.', '..'}:
        return True

    all_patterns = gitignore_patterns + extra_patterns

    for pattern in all_patterns:
        pattern = pattern.strip()
        if not pattern or pattern.startswith('#'):
            continue

        if pattern.endswith('/'):
            pattern = pattern.rstrip('/')
            if path.is_dir():
                if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_path_str, pattern):
                    return True
                if fnmatch.fnmatch(name, pattern + '/*') or fnmatch.fnmatch(rel_path_str, pattern + '/*'):
                    return True
        else:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_path_str, pattern):
                return True
            if fnmatch.fnmatch(rel_path_str, pattern + '/*'):
                return True
            for part in rel_path.parts:
                if fnmatch.fnmatch(part, pattern):
                    return True

    return False


def generate_tree(directory: Path, prefix: str = "", is_last: bool = True,
                  base_dir: Optional[Path] = None, gitignore_patterns: Optional[List[str]] = None,
                  extra_patterns: Optional[List[str]] = None, show_hidden: bool = False,
                  use_git_ignore: bool = False) -> List[str]:
    """
    Generate tree structure recursively.

    Returns list of lines representing the tree.
    """
    if base_dir is None:
        base_dir = directory
    if gitignore_patterns is None:
        gitignore_patterns = []
    if extra_patterns is None:
        extra_patterns = []

    if use_git_ignore and directory == base_dir:
        gitignore_file = directory / '.gitignore'
        gitignore_patterns = parse_gitignore(gitignore_file)

    lines = []

    try:
        entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return lines

    entries = [
        e for e in entries
        if not should_ignore(e, base_dir, gitignore_patterns, extra_patterns, show_hidden)
    ]

    for i, entry in enumerate(entries):
        is_last_entry = (i == len(entries) - 1)

        connector = "└── " if is_last_entry else "├── "
        display_name = entry.name

        lines.append(f"{prefix}{connector}{display_name}")

        if entry.is_dir():
            extension = "   " if is_last_entry else "│  "
            sub_lines = generate_tree(
                entry,
                prefix + extension,
                is_last_entry,
                base_dir,
                gitignore_patterns,
                extra_patterns,
                show_hidden,
                use_git_ignore
            )
            lines.extend(sub_lines)

    return lines


def main():
    parser = argparse.ArgumentParser(description='Generate directory tree')
    parser.add_argument('path', nargs='?', default='.', help='Directory path')
    parser.add_argument('--all', '-a', action='store_true', help='Show hidden files')
    parser.add_argument('--git-ignore', action='store_true', help='Respect .gitignore')
    parser.add_argument('--ignore-glob', type=str, help='Additional patterns to ignore (pipe-separated)')
    parser.add_argument('--classify', '-F', action='store_true', help='Append indicator to entries (already done for dirs)')
    parser.add_argument('--icons', action='store_true', help='Show icons (ignored, for compatibility)')
    parser.add_argument('--tree', action='store_true', help='Display as tree (always true)')

    args = parser.parse_args()

    directory = Path(args.path).resolve()

    if not directory.exists():
        print(f"Error: {directory} does not exist", file=sys.stderr)
        sys.exit(1)

    if not directory.is_dir():
        print(f"Error: {directory} is not a directory", file=sys.stderr)
        sys.exit(1)

    extra_patterns = []
    if args.ignore_glob:
        extra_patterns = [p.strip() for p in args.ignore_glob.split('|')]

    print(".")
    lines = generate_tree(
        directory,
        "",
        True,
        directory,
        [],
        extra_patterns,
        args.all,
        args.git_ignore
    )

    for line in lines:
        print(line)


if __name__ == '__main__':
    main()
