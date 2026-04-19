"""Source/context generation API routes."""

from flask import Blueprint, request, jsonify, make_response
import ast
import json
import logging
import pathlib
import re

logger = logging.getLogger("serve.source")

source_bp = Blueprint('source', __name__, url_prefix='/api/source')


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


def _get_docstring_end_line(node: ast.AST) -> int:
    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
        return node.body[0].end_lineno
    return node.lineno


def _has_body_beyond_docstring(node: ast.AST) -> bool:
    return node.body and not (len(node.body) == 1 and isinstance(node.body[0], ast.Expr))


def _get_python_definitions(filepath: pathlib.Path) -> str:
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
            end_line = _get_docstring_end_line(node)
            def_lines = lines[start_line:end_line]
            if _has_body_beyond_docstring(node):
                def_lines.append("    ...")
            definitions.append('\n'.join(def_lines))
    return '\n\n'.join(definitions)


def _extract_function_signature(lines: list[str], start: int) -> str:
    sig_lines = []
    i = start
    paren_depth = 0
    while i < len(lines):
        line = lines[i].rstrip()
        for idx, char in enumerate(line):
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == '{' and paren_depth == 0:
                before_brace = line[:idx].rstrip()
                sig_lines.append(before_brace + ' { ... }')
                return '\n'.join(sig_lines)
        sig_lines.append(line)
        i += 1
    return '\n'.join(sig_lines)


def _extract_arrow_function_signature(lines: list[str], start: int) -> str:
    line = lines[start].rstrip()
    if '{' in line and '}' in line:
        match = re.match(r'(.*?)\s*=>\s*\{.*\}', line)
        if match:
            return match.group(1) + ' => { ... }'
        return line.split('{')[0].rstrip() + ' => { ... }'
    if '=>' in line:
        before_arrow = line.split('=>')[0].rstrip()
        return before_arrow + ' => { ... }'
    return line


def _extract_class_signature(lines: list[str], start: int) -> str:
    sig_lines = []
    i = start
    line = lines[i].rstrip()
    if '{' in line:
        sig_lines.append(line.split('{')[0].rstrip() + ' {')
    else:
        sig_lines.append(line)
    i += 1
    indent = '  '
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if stripped == '}' and not line.startswith('  '):
            sig_lines.append('}')
            break
        if re.match(r'\w+\s*\(', stripped):
            method_sig = indent + stripped.split('{')[0].rstrip() + ' { ... }'
            sig_lines.append(method_sig)
        i += 1
    return '\n'.join(sig_lines)


def _skip_to_end_of_block(lines: list[str], start: int) -> int:
    depth = 0
    i = start
    for line in lines[start:]:
        depth += line.count('{') - line.count('}')
        i += 1
        if depth == 0:
            break
    return i


def _skip_to_end_of_statement(lines: list[str], start: int) -> int:
    i = start
    while i < len(lines):
        if lines[i].rstrip().endswith((';', ',')) or '}' in lines[i]:
            return i + 1
        i += 1
    return i


def _get_js_signatures(filepath: pathlib.Path) -> str:
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    lines = content.splitlines()
    output = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.strip().startswith('import '):
            output.append(line)
            i += 1
            continue
        if line.strip().startswith('/**'):
            jsdoc = [line]
            i += 1
            while i < len(lines) and not lines[i].strip().endswith('*/'):
                jsdoc.append(lines[i].rstrip())
                i += 1
            if i < len(lines):
                jsdoc.append(lines[i].rstrip())
                i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines):
                next_line = lines[i].strip()
                if (next_line.startswith(('export ', 'function ', 'async ', 'const ', 'let ', 'var ', 'class ')) or
                    re.match(r'^(export\s+)?(default\s+)?(async\s+)?function\s+\w+', next_line) or
                    re.match(r'^(export\s+)?(const|let|var)\s+\w+\s*=', next_line)):
                    output.extend(jsdoc)
            continue
        if re.match(r'^(export\s+)?(default\s+)?(async\s+)?function\s+\w+', line):
            sig = _extract_function_signature(lines, i)
            output.append(sig)
            i = _skip_to_end_of_block(lines, i)
            continue
        match = re.match(r'^(export\s+)?(const|let|var)\s+(\w+)\s*=\s*(\([^)]*\)|[\w]+)\s*=>', line)
        if match:
            sig = _extract_arrow_function_signature(lines, i)
            output.append(sig)
            i = _skip_to_end_of_statement(lines, i)
            continue
        if re.match(r'^(export\s+)?(default\s+)?class\s+\w+', line):
            sig = _extract_class_signature(lines, i)
            output.append(sig)
            i = _skip_to_end_of_block(lines, i)
            continue
        if line.strip().startswith('export ') and '{' in line:
            output.append(line)
            i += 1
            continue
        i += 1
    return '\n'.join(output)


def _should_exclude(path: pathlib.Path, excludes: set[str]) -> bool:
    for part in path.parts:
        if part in excludes or part.startswith('.'):
            return True
    name = path.name
    return name.startswith('.') or name.endswith(('.lock', '.code-workspace')) or name in CONFIG_FILES


def _read_file_content(filepath: pathlib.Path) -> str:
    with open(filepath, encoding='utf-8', errors='ignore') as f:
        return f.read()


def _wrap_in_xml_tag(rel_path: pathlib.Path, content: str) -> list[str]:
    return [f'<file path="{rel_path}">', content, '</file>']


def _format_files_output(file_paths: list[pathlib.Path], root_dir: pathlib.Path, content_getter) -> str:
    output = ['<files>']
    for file_path in sorted(file_paths):
        rel_path = file_path.relative_to(root_dir)
        content = content_getter(file_path)
        output.extend(_wrap_in_xml_tag(rel_path, content))
    output.append('</files>')
    return '\n'.join(output)


def _find_files(root_dir: pathlib.Path, pattern: str, excludes: set[str]) -> list[pathlib.Path]:
    return sorted(
        p for p in root_dir.glob(pattern)
        if p.is_file() and not _should_exclude(p.relative_to(root_dir), excludes)
    )


def _find_files_recursive(root_dir: pathlib.Path, extensions: set[str], excludes: set[str]) -> list[pathlib.Path]:
    return sorted(
        p for p in root_dir.rglob('*')
        if p.is_file() and p.suffix in extensions and not _should_exclude(p.relative_to(root_dir), excludes)
    )


def _generate_server_context(root_dir: pathlib.Path, no_body: bool) -> str:
    python_files = _find_files(root_dir, '*.py', SERVER_EXCLUDES)
    content_getter = _get_python_definitions if no_body else _read_file_content
    return _format_files_output(python_files, root_dir, content_getter)


def _generate_client_context(root_dir: pathlib.Path, no_body: bool = False) -> str:
    client_dir = root_dir / 'client'
    if not client_dir.exists():
        return '<files>\n</files>'
    files = _find_files_recursive(client_dir, CLIENT_EXTENSIONS, COMMON_EXCLUDES)
    if no_body:
        def content_getter(filepath: pathlib.Path) -> str:
            if filepath.suffix in {'.js', '.jsx'}:
                return _get_js_signatures(filepath)
            return _read_file_content(filepath)
        return _format_files_output(files, root_dir, content_getter)
    return _format_files_output(files, root_dir, _read_file_content)


def _find_markdown_files(root_dir: pathlib.Path, excludes: set[str]) -> list[pathlib.Path]:
    return sorted(
        p for p in root_dir.rglob('*.md')
        if not _should_exclude(p.relative_to(root_dir), excludes)
    )


def _generate_docs_context(root_dir: pathlib.Path) -> str:
    all_md_files = _find_markdown_files(root_dir, DOCS_EXCLUDES)
    return _format_files_output(all_md_files, root_dir, _read_file_content)


def run_context_script(context_types, only_definitions=True):
    """Generate context for one or more context types.

    >>> run_context_script(['docs']) # doctest: +SKIP
    '<files>...</files>'
    """
    root_dir = pathlib.Path(__file__).parent
    logger.info(f"context_types={context_types}, only_definitions={only_definitions}")
    contents = []
    for ctx in context_types:
        if ctx == 'server':
            content = _generate_server_context(root_dir, only_definitions)
        elif ctx == 'client':
            content = _generate_client_context(root_dir, only_definitions)
        elif ctx == 'docs':
            content = _generate_docs_context(root_dir)
        else:
            raise ValueError(f"Unknown context type: {ctx}")
        file_count = content.count('<file path=')
        logger.info(f"{ctx} file count={file_count}")
        contents.append(content)
    return '\n\n'.join(contents)


@source_bp.route("", methods=["GET"])
def source_ui():
    """Serve simple HTML interface for generating context files."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Generate Context</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        h1 { margin-bottom: 30px; }
        .checkbox-group { margin: 20px 0; }
        label { display: block; padding: 8px 0; cursor: pointer; }
        input[type="checkbox"] { margin-right: 10px; }
        button { margin-top: 20px; padding: 12px 24px; font-size: 16px; 
                 background: #007bff; color: white; border: none; 
                 border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        button:disabled { background: #ccc; cursor: not-allowed; }
    </style>
</head>
<body>
    <h1>Generate Context</h1>
    <form id="contextForm">
        <div class="checkbox-group">
            <label><input type="checkbox" name="context" value="docs"> Documentation</label>
            <label><input type="checkbox" name="context" value="server"> Server (Python)</label>
            <label><input type="checkbox" name="context" value="client"> Client (React)</label>
        </div>
        <div class="checkbox-group">
            <label><input type="checkbox" name="only_definitions" id="onlyDefinitions"> Only signatures (no function bodies - applies to Server + Client)</label>
        </div>
        <button type="submit">Download Context</button>
    </form>
    <script>
        document.getElementById('contextForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const checked = Array.from(document.querySelectorAll('input[name="context"]:checked'))
                .map(cb => cb.value);

            if (checked.length === 0) {
                alert('Please select at least one context type');
                return;
            }

            const onlyDefinitions = document.getElementById('onlyDefinitions').checked;

            const form = new FormData();
            form.append('context_types', JSON.stringify(checked));
            form.append('only_definitions', onlyDefinitions);

            const response = await fetch('/api/source/download', {
                method: 'POST',
                body: form
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = response.headers.get('Content-Disposition').match(/filename="(.+)"/)[1];
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                alert('Failed to generate context');
            }
        });
    </script>
</body>
</html>"""
    return html


@source_bp.route("", methods=["POST"])
def source_json():
    """Generate context for server, client, docs, or all. Returns JSON."""
    try:
        data = request.get_json()
        context_type = data['context_type']

        if context_type not in ['server', 'client', 'docs', 'all']:
            return jsonify({"success": False, "error": "Invalid context_type. Must be 'server', 'client', 'docs', or 'all'"}), 400

        context_types = ['docs', 'server', 'client'] if context_type == 'all' else [context_type]
        combined_content = run_context_script(context_types)
        
        return jsonify({"success": True, "content": combined_content})

    except Exception as e:
        logger.error(
            "error error=%s",
            repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@source_bp.route("/download", methods=["POST"])
def source_download_post():
    """Generate context for selected types and trigger download."""
    try:
        context_types = request.form.get('context_types')
        if not context_types:
            return jsonify({"success": False, "error": "Missing context_types"}), 400

        context_types = json.loads(context_types)

        if not context_types or not all(ct in ['server', 'client', 'docs'] for ct in context_types):
            return jsonify({"success": False, "error": "Invalid context_types"}), 400

        only_definitions = request.form.get('only_definitions', 'false').lower() == 'true'

        combined_content = run_context_script(context_types, only_definitions=only_definitions)
        filename = f"context-{'-'.join(context_types)}.txt"

        response = make_response(combined_content)
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        logger.error(
            "error error=%s",
            repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500


@source_bp.route("/<context_type>", methods=["GET"])
def source_download_get(context_type):
    """Generate context for server, client, docs, or all. Triggers browser download."""
    try:
        if context_type not in ['server', 'client', 'docs', 'all']:
            return jsonify({"success": False, "error": "Invalid context_type. Must be 'server', 'client', 'docs', or 'all'"}), 400

        context_types = ['docs', 'server', 'client'] if context_type == 'all' else [context_type]
        combined_content = run_context_script(context_types)
        filename = f'context-{context_type}.txt'

        response = make_response(combined_content)
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        logger.error(
            "error error=%s",
            repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500

