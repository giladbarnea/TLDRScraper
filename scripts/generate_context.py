#!/usr/bin/env python3
"""Generate context files for different parts of the codebase.

Usage:
    python scripts/generate_context.py server [--no-body] > codebase.txt
    python scripts/generate_context.py client > client.txt
    python scripts/generate_context.py docs > docs.txt
"""

import argparse
import ast
import pathlib
import sys
from typing import List, Set


def get_python_definitions(filepath: pathlib.Path) -> str:
    """Extract class and function definitions with docstrings from a Python file."""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return f"# Error parsing {filepath}\n"

    lines = content.splitlines()
    definitions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start_line = node.lineno - 1

            if isinstance(node, ast.ClassDef):
                if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                    end_line = node.body[0].end_lineno
                else:
                    end_line = node.lineno
            else:
                if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                    end_line = node.body[0].end_lineno
                else:
                    end_line = node.lineno

            def_lines = lines[start_line:end_line]

            if node.body:
                if not (len(node.body) == 1 and isinstance(node.body[0], ast.Expr)):
                    def_lines.append("    ...")

            definitions.append('\n'.join(def_lines))

    return '\n\n'.join(definitions)


def should_exclude(path: pathlib.Path, excludes: Set[str]) -> bool:
    """Check if path should be excluded."""
    parts = path.parts

    for part in parts:
        if part in excludes or part.startswith('.'):
            return True

    name = path.name
    if name.startswith('.') or name.endswith(('.lock', '.code-workspace')):
        return True

    config_files = {
        'package.json', 'package-lock.json',
        'pyproject.toml', 'uv.lock',
        '.gitignore', '.gitattributes',
        'vercel.json', 'tsconfig.json', 'tsconfig.node.json',
        'vite.config.js', 'eslint.config.js'
    }

    return name in config_files


def find_files(root_dir: pathlib.Path, pattern: str, excludes: Set[str]) -> List[pathlib.Path]:
    """Find files matching pattern, excluding specified directories."""
    files = []
    for path in root_dir.glob(pattern):
        if path.is_file() and not should_exclude(path.relative_to(root_dir), excludes):
            files.append(path)
    return sorted(files)


def find_files_recursive(root_dir: pathlib.Path, extensions: Set[str], excludes: Set[str]) -> List[pathlib.Path]:
    """Find files with given extensions recursively."""
    files = []
    for path in root_dir.rglob('*'):
        if path.is_file() and path.suffix in extensions:
            if not should_exclude(path.relative_to(root_dir), excludes):
                files.append(path)
    return sorted(files)


def generate_server_context(root_dir: pathlib.Path, no_body: bool) -> str:
    """Generate server context with Python files only."""
    excludes = {
        'CLAUDE.md', 'thoughts', '.claude', '.git', '.github', '.githooks',
        'experimental', 'docs', 'tests', 'scripts', 'node_modules', '__pycache__',
        'api', 'static', 'dist', 'build', '.venv', 'venv', 'env', 'client'
    }

    python_files = find_files(root_dir, '*.py', excludes)

    output = ['<files>']

    for py_file in python_files:
        rel_path = py_file.relative_to(root_dir)
        output.append(f'<file path="{rel_path}">')

        if no_body:
            content = get_python_definitions(py_file)
        else:
            with open(py_file, encoding='utf-8') as f:
                content = f.read()

        output.append(content)
        output.append('</file>')

    output.append('</files>')
    return '\n'.join(output)


def generate_client_context(root_dir: pathlib.Path) -> str:
    """Generate client context with client files (excluding markdown)."""
    client_dir = root_dir / 'client'
    if not client_dir.exists():
        return '<files>\n</files>'

    excludes = {'node_modules', '__pycache__', 'dist', 'build', '.venv', 'venv', 'env'}
    extensions = {'.css', '.html', '.jsx', '.js'}

    files = []
    for path in client_dir.rglob('*'):
        if path.is_file() and path.suffix in extensions:
            rel_to_root = path.relative_to(root_dir)
            if not should_exclude(rel_to_root, excludes):
                files.append(path)

    output = ['<files>']

    for file_path in sorted(files):
        rel_path = file_path.relative_to(root_dir)
        output.append(f'<file path="{rel_path}">')
        with open(file_path, encoding='utf-8', errors='ignore') as f:
            output.append(f.read())
        output.append('</file>')

    output.append('</files>')
    return '\n'.join(output)


def generate_docs_context(root_dir: pathlib.Path) -> str:
    """Generate docs context with all markdown files (root + client)."""
    excludes = {
        'CLAUDE.md', 'thoughts', '.claude', '.git', '.github', 'node_modules',
        '__pycache__', 'dist', 'build', '.venv', 'venv', 'env',
        'experimental', 'docs', 'tests', 'scripts'
    }

    # Get root markdown files
    root_md_files = find_files(root_dir, '*.md', excludes)

    # Get client markdown files
    client_md_files = []
    client_dir = root_dir / 'client'
    if client_dir.exists():
        for path in client_dir.rglob('*.md'):
            rel_to_root = path.relative_to(root_dir)
            if not should_exclude(rel_to_root, {'node_modules', '__pycache__', 'dist', 'build'}):
                client_md_files.append(path)

    all_md_files = sorted(root_md_files + client_md_files)

    output = ['<files>']

    for md_file in all_md_files:
        rel_path = md_file.relative_to(root_dir)
        output.append(f'<file path="{rel_path}">')
        with open(md_file, encoding='utf-8') as f:
            output.append(f.read())
        output.append('</file>')

    output.append('</files>')
    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(description='Generate context files for codebase')
    parser.add_argument('context_type', choices=['server', 'client', 'docs'],
                       help='Type of context to generate')
    parser.add_argument('--no-body', action='store_true',
                       help='For server: extract only Python definitions (no implementation)')

    args = parser.parse_args()

    root_dir = pathlib.Path(__file__).parent.parent

    if args.context_type == 'server':
        content = generate_server_context(root_dir, args.no_body)
        file_count = content.count('<file path=')
        print(f"Processed Python files ({'definitions only' if args.no_body else 'full content'})", file=sys.stderr)
        print(f"Total: {file_count} files", file=sys.stderr)

    elif args.context_type == 'client':
        content = generate_client_context(root_dir)
        file_count = content.count('<file path=')
        print(f"Total: {file_count} client files", file=sys.stderr)

    elif args.context_type == 'docs':
        content = generate_docs_context(root_dir)
        file_count = content.count('<file path=')
        print(f"Total: {file_count} markdown files", file=sys.stderr)

    print(content)


if __name__ == '__main__':
    main()
