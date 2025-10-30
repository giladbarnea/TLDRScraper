#!/usr/bin/env python3
"""
Update markdown documentation frontmatter with last-updated timestamp and commit hash.
Runs as part of GitHub Actions workflow on merge operations.
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


def run_git_command(cmd: List[str]) -> str:
    """Run a git command and return its output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command {' '.join(cmd)}: {e}", file=sys.stderr)
        return ""


def get_modified_markdown_files() -> List[Path]:
    """Get list of modified or added markdown files in the most recent commit."""
    # Get files that were modified or added in the most recent commit
    output = run_git_command(["git", "diff", "--name-only", "--diff-filter=AM", "HEAD~1", "HEAD"])

    if not output:
        return []

    # Filter for markdown files
    files = [Path(f) for f in output.split('\n') if f.endswith('.md')]

    # Only return files that exist
    return [f for f in files if f.exists()]


def get_current_commit_info() -> Tuple[str, str]:
    """Get current timestamp in UTC and short commit hash."""
    # Get current time in UTC
    now = datetime.utcnow()
    timestamp = now.strftime("%Y-%m-%d %H:%M")

    # Get short commit hash (7 characters)
    commit_hash = run_git_command(["git", "rev-parse", "--short=7", "HEAD"])

    return timestamp, commit_hash


def update_frontmatter(file_path: Path, timestamp: str, commit_hash: str) -> bool:
    """
    Update the frontmatter of a markdown file.
    Returns True if the file was modified, False otherwise.
    """
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return False

    last_updated = f"last-updated: {timestamp}, {commit_hash}"

    # Pattern to match existing frontmatter
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'

    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if match:
        # File has existing frontmatter
        existing_frontmatter = match.group(1)

        # Check if last-updated field exists
        if re.search(r'last-updated:', existing_frontmatter):
            # Update existing last-updated field
            new_frontmatter = re.sub(
                r'last-updated:.*',
                last_updated,
                existing_frontmatter
            )
        else:
            # Add last-updated field to existing frontmatter
            new_frontmatter = f"{last_updated}\n{existing_frontmatter}"

        # Replace frontmatter
        new_content = re.sub(
            frontmatter_pattern,
            f"---\n{new_frontmatter}\n---\n",
            content,
            count=1,
            flags=re.DOTALL
        )
    else:
        # No frontmatter exists, create new one
        new_content = f"---\n{last_updated}\n---\n\n{content}"

    # Only write if content changed
    if new_content != content:
        try:
            file_path.write_text(new_content, encoding='utf-8')
            return True
        except Exception as e:
            print(f"Error writing {file_path}: {e}", file=sys.stderr)
            return False

    return False


def main():
    """Main function to update frontmatter for all modified markdown files."""
    # Get modified markdown files
    modified_files = get_modified_markdown_files()

    if not modified_files:
        print("No modified markdown files found.")
        return 0

    print(f"Found {len(modified_files)} modified markdown file(s):")
    for f in modified_files:
        print(f"  - {f}")

    # Get current commit info
    timestamp, commit_hash = get_current_commit_info()
    print(f"\nUpdating with timestamp: {timestamp} UTC, commit: {commit_hash}")

    # Update each file
    updated_count = 0
    for file_path in modified_files:
        if update_frontmatter(file_path, timestamp, commit_hash):
            print(f"✓ Updated: {file_path}")
            updated_count += 1
        else:
            print(f"  Skipped (no changes): {file_path}")

    print(f"\nUpdated {updated_count} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
