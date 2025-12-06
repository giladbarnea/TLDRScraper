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

COMMON_EXCLUDES = {
    'node_modules', '__pycache__', 'dist', 'build', '.venv', 'venv', 'env',
 'BUGS.md', 'GOTCHAS.md',  'CLAUDE.md', 'GEMINI.md', 'CODEX.md'
}

SERVER_EXCLUDES = COMMON_EXCLUDES | {
    'thoughts', '.claude', '.git', '.github', '.githooks',
    'experimental', 'docs', 'tests', 'scripts', 'api', 'static', 'client'
}

DOCS_EXCLUDES = COMMON_EXCLUDES | {
    'thoughts', '.claude', '.git', '.github',
    'experimental', 'docs', 'tests', 'scripts'
}

CONFIG_FILES = {
    'package.json', 'package-lock.json',
    'pyproject.toml', 'uv.lock',
    '.gitignore', '.gitattributes',
    'vercel.json', 'tsconfig.json', 'tsconfig.node.json',
    'vite.config.js', 'eslint.config.js'
}

CLIENT_EXTENSIONS = {'.css', '.html', '.jsx', '.js'}


def get_docstring_end_line(node: ast.AST) -> int:
    """Get the end line of docstring if present, else the definition line."""
    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
        return node.body[0].end_lineno
    return node.lineno


def has_body_beyond_docstring(node: ast.AST) -> bool:
    """Check if node has implementation beyond just a docstring."""
    return node.body and not (len(node.body) == 1 and isinstance(node.body[0], ast.Expr))


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
            end_line = get_docstring_end_line(node)
            def_lines = lines[start_line:end_line]

            if has_body_beyond_docstring(node):
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
    return name.startswith('.') or name.endswith(('.lock', '.code-workspace')) or name in CONFIG_FILES


def read_file_content(filepath: pathlib.Path) -> str:
    """Read file content with error handling."""
    with open(filepath, encoding='utf-8', errors='ignore') as f:
        return f.read()


def wrap_in_xml_tag(rel_path: pathlib.Path, content: str) -> List[str]:
    """Wrap content in XML file tags."""
    return [f'<file path="{rel_path}">', content, '</file>']


def format_files_output(file_paths: List[pathlib.Path], root_dir: pathlib.Path, content_getter) -> str:
    """Format files as XML output with content from content_getter."""
    output = ['<files>']
    
    for file_path in sorted(file_paths):
        rel_path = file_path.relative_to(root_dir)
        content = content_getter(file_path)
        output.extend(wrap_in_xml_tag(rel_path, content))
    
    output.append('</files>')
    return '\n'.join(output)


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
    python_files = find_files(root_dir, '*.py', SERVER_EXCLUDES)
    content_getter = get_python_definitions if no_body else read_file_content
    return format_files_output(python_files, root_dir, content_getter)


def generate_client_context(root_dir: pathlib.Path) -> str:
    """Generate client context with client files (excluding markdown)."""
    client_dir = root_dir / 'client'
    if not client_dir.exists():
        return '<files>\n</files>'

    files = find_files_recursive(client_dir, CLIENT_EXTENSIONS, COMMON_EXCLUDES)
    return format_files_output(files, root_dir, read_file_content)


def find_markdown_files(root_dir: pathlib.Path, excludes: Set[str]) -> List[pathlib.Path]:
    """Find all markdown files recursively, excluding specified directories."""
    md_files = []
    for path in root_dir.rglob('*.md'):
        rel_to_root = path.relative_to(root_dir)
        if not should_exclude(rel_to_root, excludes):
            md_files.append(path)
    return md_files


def generate_docs_context(root_dir: pathlib.Path) -> str:
    """Generate docs context with all markdown files (root + client)."""
    all_md_files = find_markdown_files(root_dir, DOCS_EXCLUDES)
    return format_files_output(all_md_files, root_dir, read_file_content)


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
