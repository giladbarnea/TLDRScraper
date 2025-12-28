"""Source/context generation API routes."""

from flask import Blueprint, request, jsonify, make_response
import logging
import subprocess
import pathlib
import json

logger = logging.getLogger("serve.source")

source_bp = Blueprint('source', __name__, url_prefix='/api/source')


def run_context_script(context_types, only_definitions=True):
    """Run generate_context.py script for one or more context types.

    >>> run_context_script(['docs']) # doctest: +SKIP
    '<files>...</files>'
    """
    root_dir = pathlib.Path(__file__).parent
    script_path = root_dir / 'scripts' / 'generate_context.py'
    logger.info(f"[run_context_script] __file__={__file__}")
    logger.info(f"[run_context_script] root_dir={root_dir}")
    logger.info(f"[run_context_script] script_path={script_path}")
    logger.info(f"[run_context_script] context_types={context_types}, only_definitions={only_definitions}")
    contents = []

    for ctx in context_types:
        cmd = ['python3', str(script_path), ctx]
        if ctx in ('server', 'client') and only_definitions:
            cmd.append('--no-body')
        logger.info(f"[run_context_script] running cmd={cmd} cwd={root_dir}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=root_dir
        )
        logger.info(f"[run_context_script] {ctx} returncode={result.returncode}")
        logger.info(f"[run_context_script] {ctx} stderr={result.stderr}")
        logger.info(f"[run_context_script] {ctx} stdout length={len(result.stdout)}")
        logger.info(f"[run_context_script] {ctx} stdout file count={result.stdout.count('<file path=')}")
        if result.returncode != 0:
            raise RuntimeError(f"Failed to generate {ctx} context: {result.stderr}")
        contents.append(result.stdout)

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
            "[serve.source_json] error error=%s",
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
            "[serve.source_download_post] error error=%s",
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
            "[serve.source_download_get] error error=%s",
            repr(e),
            exc_info=True,
        )
        return jsonify({"success": False, "error": repr(e)}), 500

