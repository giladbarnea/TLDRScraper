#!/usr/bin/env python3
"""
Generic CRUD operations for Markdown YAML frontmatter.
Handles reading, updating, writing, and deleting frontmatter fields,
including one-level-deep nested objects (dicts as values).
"""

import re
import sys
from pathlib import Path
import logging

logger = logging.getLogger("markdown_frontmatter")

Frontmatter = dict[str, "str | dict[str, str]"]


def _parse_frontmatter_text(text: str) -> Frontmatter:
    """
    Parse YAML frontmatter text into a dict, supporting one-level-deep nested objects.

    >>> _parse_frontmatter_text('name: foo\\ndescription: bar')
    {'name': 'foo', 'description': 'bar'}
    >>> _parse_frontmatter_text('name: foo\\nnested:\\n  url: https://x.com\\n  tag: v1')
    {'name': 'foo', 'nested': {'url': 'https://x.com', 'tag': 'v1'}}
    """
    result: Frontmatter = {}
    pending_key: str | None = None
    pending_nested: dict[str, str] = {}

    for line in text.split('\n'):
        if not line.strip():
            continue
        is_indented = line[:1] in (' ', '\t')
        if is_indented and pending_key is not None:
            if ':' in line:
                subkey, subvalue = line.strip().split(':', 1)
                pending_nested[subkey.strip()] = subvalue.strip()
        else:
            if pending_key is not None:
                result[pending_key] = pending_nested
                pending_key = None
                pending_nested = {}
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if value:
                    result[key] = value
                else:
                    pending_key = key

    if pending_key is not None:
        result[pending_key] = pending_nested

    return result


def _serialize_frontmatter(frontmatter_dict: Frontmatter) -> str:
    """
    Serialize a frontmatter dict to YAML text, supporting one-level-deep nested objects.

    >>> _serialize_frontmatter({'name': 'foo', 'nested': {'url': 'https://x.com', 'tag': 'v1'}})
    'name: foo\\nnested:\\n  url: https://x.com\\n  tag: v1'
    """
    lines = []
    for key, value in frontmatter_dict.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for subkey, subvalue in value.items():
                lines.append(f"  {subkey}: {subvalue}")
        else:
            lines.append(f"{key}: {value}")
    return '\n'.join(lines)


def _read_frontmatter(file_path: Path) -> tuple[Frontmatter, str]:
    """
    Idempotently read frontmatter from a markdown file.
    Guarantees triple-dash boundaries exist at the top of the file.
    Returns (frontmatter_dict, full_content).

    >>> import tempfile
    >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
    ...     _ = f.write('# Hello\\nWorld')
    ...     path = Path(f.name)
    >>> frontmatter, content = _read_frontmatter(path)
    >>> frontmatter
    {}
    >>> '---\\n---' in content
    True
    >>> path.unlink()
    """
    try:
        content = file_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return {}, ""
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return {}, ""

    frontmatter_pattern = r'^---\s*\n(.*?)---[ \t]*(?:\n|$)'
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if not match:
        new_content = f"---\n---\n\n{content}"
        try:
            file_path.write_text(new_content, encoding='utf-8')
        except Exception as e:
            logger.error(f"Error writing frontmatter boundaries to {file_path}: {e}")
        return {}, new_content

    frontmatter_text = match.group(1).strip()
    if not frontmatter_text:
        return {}, content

    return _parse_frontmatter_text(frontmatter_text), content


def _write_frontmatter(file_path: Path, frontmatter_dict: Frontmatter) -> None:
    """
    Write frontmatter dict to file.
    Reuses _read_frontmatter to guarantee frontmatter boundaries exist.
    """
    _, content = _read_frontmatter(file_path)

    frontmatter_text = _serialize_frontmatter(frontmatter_dict)

    frontmatter_pattern = r'^---\s*\n(.*?)---[ \t]*(?:\n|$)'
    new_content = re.sub(
        frontmatter_pattern,
        f"---\n{frontmatter_text}\n---\n",
        content,
        count=1,
        flags=re.DOTALL
    )

    try:
        file_path.write_text(new_content, encoding='utf-8')
    except Exception as e:
        logger.error(f"Error writing frontmatter to {file_path}: {e}")
        raise


def read(file_path: str | Path, *fields: str) -> Frontmatter:
    """
    Read frontmatter fields from a markdown file.
    If fields specified, returns only matching fields.
    Otherwise returns all frontmatter.
    Automatically returns empty dict if no frontmatter.

    >>> import tempfile
    >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
    ...     _ = f.write('---\\nfoo: bar\\nbaz: qux\\n---\\n\\n# Content')
    ...     path = Path(f.name)
    >>> read(path)
    {'foo': 'bar', 'baz': 'qux'}
    >>> read(path, 'foo')
    {'foo': 'bar'}
    >>> read(path, 'nonexistent')
    {}
    >>> path.unlink()
    """
    file_path = Path(file_path)
    frontmatter_dict, _ = _read_frontmatter(file_path)

    if not fields:
        return frontmatter_dict

    return {key: value for key, value in frontmatter_dict.items() if key in fields}


def update(file_path: str | Path, frontmatter: Frontmatter) -> Frontmatter:
    """
    Update/merge frontmatter fields in a markdown file.
    Overwrites fields if they exist, adds them if they don't.
    Returns all frontmatter after update.
    Logs error and returns empty dict if no frontmatter given.

    >>> import tempfile
    >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
    ...     _ = f.write('---\\nfoo: bar\\n---\\n\\n# Content')
    ...     path = Path(f.name)
    >>> update(path, {'foo': 'updated', 'new': 'field'})
    {'foo': 'updated', 'new': 'field'}
    >>> read(path)
    {'foo': 'updated', 'new': 'field'}
    >>> update(path, {'meta': {'url': 'https://x.com', 'tag': 'v1'}})
    {'foo': 'updated', 'new': 'field', 'meta': {'url': 'https://x.com', 'tag': 'v1'}}
    >>> path.unlink()
    """
    if not frontmatter:
        logger.error(f"No frontmatter provided for update operation on {file_path}")
        return {}

    file_path = Path(file_path)
    existing_frontmatter, _ = _read_frontmatter(file_path)

    updated_frontmatter = {**existing_frontmatter, **frontmatter}
    _write_frontmatter(file_path, updated_frontmatter)

    return updated_frontmatter


def write(file_path: str | Path, frontmatter: Frontmatter) -> Frontmatter:
    """
    Overwrite all frontmatter in a markdown file.
    Returns all frontmatter (which is the given frontmatter if successful).
    Logs error and returns empty dict if no frontmatter given.

    >>> import tempfile
    >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
    ...     _ = f.write('---\\nfoo: bar\\nbaz: qux\\n---\\n\\n# Content')
    ...     path = Path(f.name)
    >>> write(path, {'only': 'this'})
    {'only': 'this'}
    >>> read(path)
    {'only': 'this'}
    >>> write(path, {'nested': {'url': 'https://x.com', 'tag': 'v1'}})
    {'nested': {'url': 'https://x.com', 'tag': 'v1'}}
    >>> read(path)
    {'nested': {'url': 'https://x.com', 'tag': 'v1'}}
    >>> path.unlink()
    """
    if not frontmatter:
        logger.error(f"No frontmatter provided for write operation on {file_path}")
        return {}

    file_path = Path(file_path)
    _write_frontmatter(file_path, frontmatter)

    return frontmatter


def delete(file_path: str | Path, *fields: str) -> Frontmatter:
    """
    Delete frontmatter fields from a markdown file.
    If no fields specified, removes entire frontmatter including triple-dash boundaries.
    Lax: silently passes if any field doesn't exist.
    Returns all remaining frontmatter (empty dict if everything removed).

    >>> import tempfile
    >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
    ...     _ = f.write('---\\nfoo: bar\\nbaz: qux\\nkeep: me\\n---\\n\\n# Content')
    ...     path = Path(f.name)
    >>> delete(path, 'foo', 'nonexistent')
    {'baz': 'qux', 'keep': 'me'}
    >>> delete(path, 'baz', 'keep')
    {}
    >>> path.unlink()
    """
    file_path = Path(file_path)

    if not fields:
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return {}

        frontmatter_pattern = r'^---\s*\n(.*?)---[ \t]*(?:\n\n?|$)'
        new_content = re.sub(frontmatter_pattern, '', content, count=1, flags=re.DOTALL)

        try:
            file_path.write_text(new_content, encoding='utf-8')
        except Exception as e:
            logger.error(f"Error removing frontmatter from {file_path}: {e}")

        return {}

    existing_frontmatter, _ = _read_frontmatter(file_path)
    remaining_frontmatter = {key: value for key, value in existing_frontmatter.items() if key not in fields}

    if remaining_frontmatter:
        _write_frontmatter(file_path, remaining_frontmatter)
    else:
        delete(file_path)

    return remaining_frontmatter


def body(file_path: str | Path) -> str:
    """
    Return file content stripped of frontmatter. Pure read — no side effects.

    >>> import tempfile
    >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
    ...     _ = f.write('---\\nfoo: bar\\n---\\n\\n# Content\\nHello')
    ...     path = Path(f.name)
    >>> body(path)
    '\\n# Content\\nHello'
    >>> body(path) == body(path)
    True
    >>> path.unlink()
    """
    file_path = Path(file_path)
    try:
        content = file_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ""
    match = re.match(r'^---\s*\n(.*?)---[ \t]*(?:\n|$)', content, re.DOTALL)
    if not match:
        return content
    return content[match.end():]


def render(frontmatter_dict: Frontmatter, body_content: str) -> str:
    """
    Render a complete markdown file string with frontmatter block and body.

    >>> render({'name': 'foo', 'meta': {'url': 'https://x.com'}}, '\\n# Hello')
    '---\\nname: foo\\nmeta:\\n  url: https://x.com\\n---\\n\\n# Hello'
    """
    return f"---\n{_serialize_frontmatter(frontmatter_dict)}\n---\n{body_content}"


def update_if_body_changed(file_path: str | Path, new_body: str, frontmatter: Frontmatter) -> bool:
    """
    Write new_body + frontmatter to file only if body content differs from existing (ignoring all whitespace).
    Returns True if file was updated, False if content was identical.

    >>> import tempfile
    >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
    ...     _ = f.write('---\\nlast_updated: 2024-01-01\\n---\\n\\n# Same content')
    ...     path = Path(f.name)
    >>> update_if_body_changed(path, '\\n# Same content', {'last_updated': '2099-01-01'})
    False
    >>> update_if_body_changed(path, '\\n# Different content', {'last_updated': '2099-01-01'})
    True
    >>> path.unlink()
    """
    file_path = Path(file_path)
    existing_body = body(file_path)

    if ''.join(existing_body.split()) == ''.join(new_body.split()):
        return False

    file_path.write_text(new_body, encoding='utf-8')
    update(file_path, frontmatter)
    return True


if __name__ == "__main__":
    import doctest
    doctest.testmod()
