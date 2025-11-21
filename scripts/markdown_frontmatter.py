#!/usr/bin/env python3
"""
Generic CRUD operations for Markdown YAML frontmatter.
Handles reading, updating, writing, and deleting frontmatter fields.
"""

import re
import sys
from pathlib import Path
import logging

try:
    import util
    logger = logging.getLogger("markdown_frontmatter")
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import util
    logger = logging.getLogger("markdown_frontmatter")


def _read_frontmatter(file_path: Path) -> tuple[dict[str, str], str]:
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

    frontmatter_pattern = r'^---\s*\n(.*?)---\s*\n'
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

    frontmatter_dict = {}
    for line in frontmatter_text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            frontmatter_dict[key.strip()] = value.strip()

    return frontmatter_dict, content


def _write_frontmatter(file_path: Path, frontmatter_dict: dict[str, str]) -> None:
    """
    Write frontmatter dict to file.
    Reuses _read_frontmatter to guarantee frontmatter boundaries exist.
    """
    _, content = _read_frontmatter(file_path)

    frontmatter_lines = [f"{key}: {value}" for key, value in frontmatter_dict.items()]
    frontmatter_text = '\n'.join(frontmatter_lines)

    frontmatter_pattern = r'^---\s*\n(.*?)---\s*\n'
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


def read(file_path: str | Path, *fields: str) -> dict[str, str]:
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


def update(file_path: str | Path, frontmatter: dict[str, str]) -> dict[str, str]:
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


def write(file_path: str | Path, frontmatter: dict[str, str]) -> dict[str, str]:
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
    >>> path.unlink()
    """
    if not frontmatter:
        logger.error(f"No frontmatter provided for write operation on {file_path}")
        return {}

    file_path = Path(file_path)
    _write_frontmatter(file_path, frontmatter)

    return frontmatter


def delete(file_path: str | Path, *fields: str) -> dict[str, str]:
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

        frontmatter_pattern = r'^---\s*\n(.*?)---\s*\n\n?'
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


if __name__ == "__main__":
    import doctest
    doctest.testmod()
