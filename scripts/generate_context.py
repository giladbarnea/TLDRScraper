#!/usr/bin/env python3
"""Generate context files for different parts of the codebase.

Usage:
    python scripts/generate_context.py server [--no-body] > codebase.txt
    python scripts/generate_context.py client [--no-body] > client.txt
    python scripts/generate_context.py docs > docs.txt
"""

import argparse
import ast
import pathlib
import re
import sys
from typing import List, Set

COMMON_EXCLUDES = {
    'node_modules', '__pycache__', 'dist', 'build', '.venv', 'venv', 'env', '_vendor', '.pytest_cache',
    'BUGS.md', 'CLAUDE.md', 'GEMINI.md', 'CODEX.md'
}

SERVER_EXCLUDES = COMMON_EXCLUDES | {
    'thoughts', '.claude', '.git', '.github', '.githooks',
    'experimental', 'docs', 'tests', 'scripts', 'api', 'static', 'client',
    'vc__handler__python.py'
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


def get_js_signatures(filepath: pathlib.Path) -> str:
    """Extract signatures from JS/JSX files (like .d.ts style)."""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    lines = content.splitlines()
    output = []
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        # Keep import statements
        if line.strip().startswith('import '):
            output.append(line)
            i += 1
            continue

        # Collect JSDoc comments
        if line.strip().startswith('/**'):
            jsdoc = [line]
            i += 1
            while i < len(lines) and not lines[i].strip().endswith('*/'):
                jsdoc.append(lines[i].rstrip())
                i += 1
            if i < len(lines):
                jsdoc.append(lines[i].rstrip())
                i += 1

            # Check if next non-empty line is a function/class/export
            while i < len(lines) and not lines[i].strip():
                i += 1

            if i < len(lines):
                next_line = lines[i].strip()
                if (next_line.startswith(('export ', 'function ', 'async ', 'const ', 'let ', 'var ', 'class ')) or
                    re.match(r'^(export\s+)?(default\s+)?(async\s+)?function\s+\w+', next_line) or
                    re.match(r'^(export\s+)?(const|let|var)\s+\w+\s*=', next_line)):
                    output.extend(jsdoc)
            continue

        # Extract function declarations (including async)
        if re.match(r'^(export\s+)?(default\s+)?(async\s+)?function\s+\w+', line):
            sig = extract_function_signature(lines, i)
            output.append(sig)
            i = skip_to_end_of_block(lines, i)
            continue

        # Extract arrow function exports/declarations
        match = re.match(r'^(export\s+)?(const|let|var)\s+(\w+)\s*=\s*(\([^)]*\)|[\w]+)\s*=>', line)
        if match:
            sig = extract_arrow_function_signature(lines, i)
            output.append(sig)
            i = skip_to_end_of_statement(lines, i)
            continue

        # Extract class declarations
        if re.match(r'^(export\s+)?(default\s+)?class\s+\w+', line):
            sig = extract_class_signature(lines, i)
            output.append(sig)
            i = skip_to_end_of_block(lines, i)
            continue

        # Keep standalone export statements
        if line.strip().startswith('export ') and '{' in line:
            output.append(line)
            i += 1
            continue

        i += 1

    return '\n'.join(output)


def extract_function_signature(lines: List[str], start: int) -> str:
    """Extract function signature up to opening brace (function body start)."""
    sig_lines = []
    i = start
    paren_depth = 0

    while i < len(lines):
        line = lines[i].rstrip()

        # Track parenthesis depth to find function body start, not param destructuring
        for idx, char in enumerate(line):
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == '{' and paren_depth == 0:
                # This is the function body opening brace
                before_brace = line[:idx].rstrip()
                sig_lines.append(before_brace + ' { ... }')
                return '\n'.join(sig_lines)

        sig_lines.append(line)
        i += 1

    return '\n'.join(sig_lines)


def extract_arrow_function_signature(lines: List[str], start: int) -> str:
    """Extract arrow function signature."""
    line = lines[start].rstrip()

    # Simple case: single line
    if '{' in line and '}' in line:
        match = re.match(r'(.*?)\s*=>\s*\{.*\}', line)
        if match:
            return match.group(1) + ' => { ... }'
        return line.split('{')[0].rstrip() + ' => { ... }'

    # Multi-line case
    if '=>' in line:
        before_arrow = line.split('=>')[0].rstrip()
        return before_arrow + ' => { ... }'

    return line


def extract_class_signature(lines: List[str], start: int) -> str:
    """Extract class name and method signatures."""
    sig_lines = []
    i = start

    # Add class declaration
    line = lines[i].rstrip()
    if '{' in line:
        sig_lines.append(line.split('{')[0].rstrip() + ' {')
    else:
        sig_lines.append(line)

    i += 1
    indent = '  '

    # Extract method signatures
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        # End of class
        if stripped == '}' and not line.startswith('  '):
            sig_lines.append('}')
            break

        # Method declaration
        if re.match(r'\w+\s*\(', stripped):
            method_sig = indent + stripped.split('{')[0].rstrip() + ' { ... }'
            sig_lines.append(method_sig)

        i += 1

    return '\n'.join(sig_lines)


def skip_to_end_of_block(lines: List[str], start: int) -> int:
    """Skip to the closing brace of a block."""
    depth = 0
    i = start

    for line in lines[start:]:
        depth += line.count('{') - line.count('}')
        i += 1
        if depth == 0:
            break

    return i


def skip_to_end_of_statement(lines: List[str], start: int) -> int:
    """Skip to end of statement (handles multiline)."""
    i = start

    while i < len(lines):
        if lines[i].rstrip().endswith((';', ',')) or '}' in lines[i]:
            return i + 1
        i += 1

    return i


def extract_component_definitions(filepath: pathlib.Path) -> List[str]:
    """Extract React component names defined in a file.

    Looks for:
    - function ComponentName(...)
    - const ComponentName = (...) =>
    - class ComponentName
    """
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    components = []

    # Match function declarations: function ComponentName(
    for match in re.finditer(r'^\s*(?:export\s+(?:default\s+)?)?function\s+([A-Z]\w*)\s*\(', content, re.MULTILINE):
        components.append(match.group(1))

    # Match arrow function declarations: const ComponentName = (...) =>
    for match in re.finditer(r'^\s*(?:export\s+(?:default\s+)?)?const\s+([A-Z]\w*)\s*=\s*(?:\([^)]*\)|[\w]+)\s*=>', content, re.MULTILINE):
        components.append(match.group(1))

    # Match class declarations: class ComponentName
    for match in re.finditer(r'^\s*(?:export\s+(?:default\s+)?)?class\s+([A-Z]\w*)', content, re.MULTILINE):
        components.append(match.group(1))

    return list(set(components))


def extract_hook_definitions(filepath: pathlib.Path) -> List[str]:
    """Extract custom React hook names defined in a file.

    Custom hooks are functions that start with 'use' (React convention).
    """
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    hooks = []

    # Match function declarations: function useHookName(
    for match in re.finditer(r'^\s*(?:export\s+(?:default\s+)?)?function\s+(use[A-Z]\w*)\s*\(', content, re.MULTILINE):
        hooks.append(match.group(1))

    # Match arrow function declarations: const useHookName = (...) =>
    for match in re.finditer(r'^\s*(?:export\s+(?:default\s+)?)?const\s+(use[A-Z]\w*)\s*=\s*(?:\([^)]*\)|[\w]+)\s*=>', content, re.MULTILINE):
        hooks.append(match.group(1))

    return list(set(hooks))


def find_component_usage(component_name: str, filepath: pathlib.Path) -> List[tuple]:
    """Find JSX usages of a component with full prop information.

    Returns list of (line_number, usage_lines) tuples where usage_lines may span multiple lines.
    """
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    usages = []
    pattern = re.compile(rf'<{component_name}(?:\s|>|/)')

    i = 0
    while i < len(lines):
        line = lines[i]

        if pattern.search(line):
            # Capture the full JSX tag (may span multiple lines)
            usage_lines = [line.rstrip()]
            line_num = i + 1

            # Check if tag is self-closing or has closing bracket on same line
            if '/>' in line or '>' in line and not line.rstrip().endswith(('{', ',')):
                usages.append((line_num, usage_lines[0]))
                i += 1
                continue

            # Multi-line JSX tag - continue until we find the closing
            i += 1
            depth = 1  # Track bracket depth for complex props
            while i < len(lines) and depth > 0:
                next_line = lines[i].rstrip()
                usage_lines.append(next_line)

                # Simple heuristic: look for closing > or />
                if '/>' in next_line or ('>' in next_line and '{' not in next_line):
                    break

                i += 1

            # Join the lines for display (limit to reasonable length)
            full_usage = ' '.join(usage_lines)
            if len(full_usage) > 200:
                full_usage = full_usage[:200] + '...'

            usages.append((line_num, full_usage))

        i += 1

    return usages


def find_hook_usage(hook_name: str, filepath: pathlib.Path) -> List[tuple]:
    """Find calls to a hook in a file.

    Returns list of (line_number, usage_line) tuples.
    """
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    usages = []
    pattern = re.compile(rf'\b{hook_name}\s*\(')

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip comment lines
        if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
            continue

        if pattern.search(line):
            usages.append((i, stripped))

    return usages


def build_call_site_maps(client_dir: pathlib.Path) -> tuple:
    """Build component and hook definition -> usage maps for the entire client directory.

    Returns (component_map, hook_map) where each map is:
        {
            'Name': {
                'defined_in': 'relative/path/to/file.jsx',
                'used_in': [('file.jsx', line_num, usage_str), ...]
            }
        }
    """
    if not client_dir.exists():
        return {}, {}

    js_files = list(client_dir.rglob('*.js')) + list(client_dir.rglob('*.jsx'))
    js_files = [f for f in js_files if f.is_file() and 'node_modules' not in f.parts]

    component_map = {}
    hook_map = {}

    # Step 1: Find all definitions
    for filepath in js_files:
        rel_path = filepath.relative_to(client_dir.parent)

        # Find components
        components = extract_component_definitions(filepath)
        for component in components:
            if component not in component_map:
                component_map[component] = {
                    'defined_in': str(rel_path),
                    'used_in': []
                }

        # Find hooks
        hooks = extract_hook_definitions(filepath)
        for hook in hooks:
            if hook not in hook_map:
                hook_map[hook] = {
                    'defined_in': str(rel_path),
                    'used_in': []
                }

    # Step 2: Find all usages
    for filepath in js_files:
        rel_path = filepath.relative_to(client_dir.parent)

        # Find component usages
        for component_name in component_map.keys():
            usages = find_component_usage(component_name, filepath)
            for line_num, usage_str in usages:
                component_map[component_name]['used_in'].append((str(rel_path), line_num, usage_str))

        # Find hook usages
        for hook_name in hook_map.keys():
            usages = find_hook_usage(hook_name, filepath)
            for line_num, usage_str in usages:
                # Don't count the definition itself as a usage
                if str(rel_path) != hook_map[hook_name]['defined_in'] or not usage_str.startswith(('function', 'const', 'export')):
                    hook_map[hook_name]['used_in'].append((str(rel_path), line_num, usage_str))

    return component_map, hook_map


def append_call_sites_to_signatures(signatures: str, filepath: pathlib.Path, component_map: dict, hook_map: dict, root_dir: pathlib.Path) -> str:
    """Append call site information to the signatures output."""
    rel_path = str(filepath.relative_to(root_dir))

    # Find components and hooks defined in this file
    components_in_file = [name for name, info in component_map.items() if info['defined_in'] == rel_path]
    hooks_in_file = [name for name, info in hook_map.items() if info['defined_in'] == rel_path]

    if not components_in_file and not hooks_in_file:
        return signatures

    call_sites = ['\n', '// === Call Sites ===', '']

    # Add component call sites
    for component_name in sorted(components_in_file):
        info = component_map[component_name]
        if info['used_in']:
            call_sites.append(f"// {component_name} is used in:")
            for file_path, line_num, usage in info['used_in'][:5]:  # Show first 5
                call_sites.append(f"//   {file_path}:{line_num}")
                call_sites.append(f"//     {usage}")
            if len(info['used_in']) > 5:
                call_sites.append(f"//   ... and {len(info['used_in']) - 5} more places")
            call_sites.append('')

    # Add hook call sites
    for hook_name in sorted(hooks_in_file):
        info = hook_map[hook_name]
        if info['used_in']:
            call_sites.append(f"// {hook_name} is called in:")
            for file_path, line_num, usage in info['used_in'][:5]:  # Show first 5
                call_sites.append(f"//   {file_path}:{line_num}")
                call_sites.append(f"//     {usage}")
            if len(info['used_in']) > 5:
                call_sites.append(f"//   ... and {len(info['used_in']) - 5} more places")
            call_sites.append('')

    return signatures + '\n'.join(call_sites)


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


def generate_client_context(root_dir: pathlib.Path, no_body: bool = False) -> str:
    """Generate client context with client files (excluding markdown)."""
    client_dir = root_dir / 'client'
    if not client_dir.exists():
        return '<files>\n</files>'

    files = find_files_recursive(client_dir, CLIENT_EXTENSIONS, COMMON_EXCLUDES)

    if no_body:
        # Build call site maps for components and hooks
        component_map, hook_map = build_call_site_maps(client_dir)

        def content_getter(filepath: pathlib.Path) -> str:
            if filepath.suffix in {'.js', '.jsx'}:
                signatures = get_js_signatures(filepath)
                # Append call site information
                return append_call_sites_to_signatures(signatures, filepath, component_map, hook_map, root_dir)
            return read_file_content(filepath)
        return format_files_output(files, root_dir, content_getter)

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
                       help='Extract only signatures (server: Python definitions, client: JS/JSX signatures)')

    args = parser.parse_args()

    root_dir = pathlib.Path(__file__).parent.parent

    if args.context_type == 'server':
        content = generate_server_context(root_dir, args.no_body)
        file_count = content.count('<file path=')
        print(f"Processed Python files ({'definitions only' if args.no_body else 'full content'})", file=sys.stderr)
        print(f"Total: {file_count} files", file=sys.stderr)

    elif args.context_type == 'client':
        content = generate_client_context(root_dir, args.no_body)
        file_count = content.count('<file path=')
        mode = 'signatures only (JS/JSX)' if args.no_body else 'full content'
        print(f"Processed client files ({mode})", file=sys.stderr)
        print(f"Total: {file_count} files", file=sys.stderr)

    elif args.context_type == 'docs':
        content = generate_docs_context(root_dir)
        file_count = content.count('<file path=')
        print(f"Total: {file_count} markdown files", file=sys.stderr)

    print(content)


if __name__ == '__main__':
    main()
