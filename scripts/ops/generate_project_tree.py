#!/usr/bin/env python3
"""
Generate a directory tree structure similar to 'eza --tree'.
Drop-in replacement for eza to avoid installation time.

Usage:
    python generate_tree.py [--all] [--git-ignore] [--ignore-glob PATTERNS] [PATH]
"""

import sys
import fnmatch
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional, Set


def git_ignored_paths(base_dir: Path) -> Set[str]:
    """Paths git ignores under base_dir, honoring .gitignore, .git/info/exclude, and global excludes.

    Delegates to git so the full ignore stack is respected (not just the repo-root .gitignore).
    Directory entries are returned without their trailing slash. Returns an empty set outside a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "-o", "-i", "--exclude-standard", "--directory", "-z"],
            cwd=base_dir,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()
    return {entry.rstrip('/') for entry in result.stdout.split('\0') if entry}


def should_ignore(path: Path, base_dir: Path, git_ignored: Set[str],
                  extra_patterns: List[str], show_hidden: bool) -> bool:
    """
    Check if a path should be ignored based on git's ignore stack and the extra --ignore-glob patterns.

    >>> should_ignore(Path('node_modules'), Path('.'), {'node_modules'}, [], True)
    True
    >>> should_ignore(Path('experimental'), Path('.'), set(), ['experimental'], True)
    True
    >>> should_ignore(Path('.hidden'), Path('.'), set(), [], False)
    True
    >>> should_ignore(Path('.hidden'), Path('.'), set(), [], True)
    False
    """
    rel_path = path.relative_to(base_dir)
    rel_path_str = str(rel_path)
    name = path.name

    if not show_hidden and name.startswith('.') and name not in {'.', '..'}:
        return True

    if rel_path_str in git_ignored:
        return True

    for pattern in extra_patterns:
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
                  base_dir: Optional[Path] = None, git_ignored: Optional[Set[str]] = None,
                  extra_patterns: Optional[List[str]] = None, show_hidden: bool = False) -> List[str]:
    """
    Generate tree structure recursively.

    Returns list of lines representing the tree.
    """
    if base_dir is None:
        base_dir = directory
    if git_ignored is None:
        git_ignored = set()
    if extra_patterns is None:
        extra_patterns = []

    lines = []

    try:
        entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return lines

    entries = [
        e for e in entries
        if not should_ignore(e, base_dir, git_ignored, extra_patterns, show_hidden)
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
                git_ignored,
                extra_patterns,
                show_hidden
            )
            lines.extend(sub_lines)

    return lines


def main():
    parser = argparse.ArgumentParser(description='Generate directory tree')
    parser.add_argument('path', nargs='?', default='.', help='Directory path')
    parser.add_argument('--all', '-a', action='store_true', help='Show hidden files')
    parser.add_argument('--git-ignore', action='store_true', default=True, help='Respect .gitignore (default: True)')
    parser.add_argument('--no-git-ignore', action='store_false', dest='git_ignore', help='Do not respect .gitignore')
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

    git_ignored = git_ignored_paths(directory) if args.git_ignore else set()

    print(".")
    lines = generate_tree(
        directory,
        "",
        True,
        directory,
        git_ignored,
        extra_patterns,
        args.all
    )

    for line in lines:
        print(line)


if __name__ == '__main__':
    main()
