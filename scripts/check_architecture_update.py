#!/usr/bin/env python3
"""
Check if ARCHITECTURE.md should be updated based on code changes.
Can be used as a pre-commit hook, pre-push hook, or CI check.

Usage:
    # Check current commit
    python check_architecture_update.py

    # Check specific commit
    python check_architecture_update.py <commit-hash>

    # Check range of commits
    python check_architecture_update.py <start-commit>..<end-commit>

Exit codes:
    0 = No update needed (or already updated)
    1 = Update needed but missing
    2 = Manual review recommended
"""

import subprocess
import sys
from pathlib import Path


def run_git(cmd):
    """Run git command and return output."""
    result = subprocess.run(
        f"git {cmd}",
        shell=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    return result.stdout.strip()


def get_changed_files(commit_ref='HEAD'):
    """Get list of changed files in commit."""
    output = run_git(f"diff-tree --no-commit-id --name-only -r -m --first-parent {commit_ref}")
    return [f for f in output.split('\n') if f]


def get_commit_message(commit_ref='HEAD'):
    """Get commit message."""
    return run_git(f"log -1 --format=%s {commit_ref}")


def architecture_already_updated(commit_ref='HEAD'):
    """Check if ARCHITECTURE.md body was updated in this commit."""
    files = get_changed_files(commit_ref)

    if 'ARCHITECTURE.md' not in files:
        return False

    # Check if it's only frontmatter
    diff = run_git(f"show {commit_ref} -- ARCHITECTURE.md")
    diff_lines = [l for l in diff.split('\n') if l.startswith('+') or l.startswith('-')]
    diff_lines = [l for l in diff_lines if not l.startswith('+++') and not l.startswith('---')]

    frontmatter_changes = [l for l in diff_lines if 'last_updated' in l]
    non_frontmatter_changes = [l for l in diff_lines if 'last_updated' not in l]

    # If only frontmatter changed, consider it not updated
    return len(non_frontmatter_changes) > 0


def should_update_architecture(commit_ref='HEAD'):
    """
    Heuristic to determine if ARCHITECTURE.md should be updated.

    Returns:
        - 'yes': Update needed
        - 'no': Update not needed
        - 'maybe': Unclear, manual review recommended
    """
    files = get_changed_files(commit_ref)
    message = get_commit_message(commit_ref).lower()

    # If architecture already updated, we're good
    if architecture_already_updated(commit_ref):
        return 'no'  # Already updated, so no action needed

    # Count file types
    jsx_components = sum(1 for f in files if f.startswith('client/src/components/') and f.endswith('.jsx'))
    js_hooks = sum(1 for f in files if f.startswith('client/src/hooks/') and f.endswith('.js'))
    css_files = sum(1 for f in files if f.endswith('.css'))
    py_adapters = sum(1 for f in files if f.startswith('adapters/') or f.endswith('_adapter.py'))
    md_docs = sum(1 for f in files if f.endswith('.md') and f != 'ARCHITECTURE.md')
    config_files = sum(1 for f in files if any(x in f for x in
        ['package.json', 'package-lock.json', 'vite.config', 'vercel.json', '.yml', '.yaml', '.githooks', '.github']))

    # Total non-trivial files (excluding ARCHITECTURE.md)
    total_files = len([f for f in files if f and f != 'ARCHITECTURE.md'])

    # Check for ONLY certain file types (strong negative indicators)
    if total_files > 0:
        if css_files == total_files:
            return 'no'  # CSS-only changes

        if py_adapters == total_files:
            return 'no'  # Adapter-only changes

        if md_docs == total_files:
            return 'no'  # Docs-only changes

        if config_files == total_files:
            return 'no'  # Config-only changes

        # Check for lock files / auto-generated files
        auto_generated = sum(1 for f in files if any(x in f for x in
            ['package-lock.json', 'uv.lock', 'pyproject.toml', '-lock.']))
        if auto_generated == total_files:
            return 'no'  # Lock file updates only

    # Check commit message keywords
    behavior_keywords = ['behavior', 'behaviour', 'change how', 'now', 'instead',
                        'auto-fold', 'auto-collapse', 'reposition', 'sort']
    component_keywords = ['component', 'jsx', 'ui', 'display', 'interaction', 'flow',
                         'user', 'click', 'button', 'container', 'layout']
    trivial_keywords = ['fix typo', 'fix spacing', 'cleanup', 'format', 'lint',
                       'comment', 'log', 'debug', 'test']

    has_behavior_change = any(kw in message for kw in behavior_keywords)
    has_component_change = any(kw in message for kw in component_keywords)
    is_trivial = any(kw in message for kw in trivial_keywords)

    # Check for fix-only commits (usually don't need architecture updates)
    is_fix_only = message.startswith('fix:') and not has_behavior_change

    # Decision logic
    if is_trivial:
        return 'no'

    if is_fix_only and jsx_components == 0:
        return 'no'

    # Strong positive indicators
    if jsx_components >= 1 and (has_component_change or has_behavior_change):
        return 'yes'

    if js_hooks >= 1:
        return 'yes'

    # Moderate indicator - might need manual review
    if jsx_components >= 2:
        return 'maybe'

    # Default: no update needed
    return 'no'


def main():
    commit_ref = sys.argv[1] if len(sys.argv) > 1 else 'HEAD'

    # Check if it's a range
    if '..' in commit_ref:
        # For ranges, check each commit
        commits = run_git(f"log --format=%H {commit_ref}").split('\n')
        results = []
        for commit in commits:
            if commit:
                result = should_update_architecture(commit)
                msg = get_commit_message(commit)
                results.append((commit[:8], msg, result))

        # Summary
        needs_update = [r for r in results if r[2] == 'yes']
        maybe_update = [r for r in results if r[2] == 'maybe']

        if needs_update:
            print(f"\n⚠️  ARCHITECTURE.md UPDATE NEEDED for {len(needs_update)} commit(s):\n")
            for commit, msg, _ in needs_update:
                print(f"  {commit}: {msg}")
            if maybe_update:
                print(f"\n❓ MANUAL REVIEW RECOMMENDED for {len(maybe_update)} commit(s):\n")
                for commit, msg, _ in maybe_update:
                    print(f"  {commit}: {msg}")
            sys.exit(1)
        elif maybe_update:
            print(f"\n❓ MANUAL REVIEW RECOMMENDED for {len(maybe_update)} commit(s):\n")
            for commit, msg, _ in maybe_update:
                print(f"  {commit}: {msg}")
            print("\nThese changes may require architecture documentation updates.")
            sys.exit(2)
        else:
            print("✅ No architecture updates needed")
            sys.exit(0)
    else:
        # Single commit check
        result = should_update_architecture(commit_ref)
        msg = get_commit_message(commit_ref)

        if result == 'yes':
            print(f"\n⚠️  ARCHITECTURE.md UPDATE NEEDED\n")
            print(f"Commit: {commit_ref[:8]}")
            print(f"Message: {msg}")
            print(f"\nThis commit changes user-facing behavior or component structure.")
            print(f"Please update ARCHITECTURE.md to reflect these changes.\n")
            sys.exit(1)
        elif result == 'maybe':
            print(f"\n❓ MANUAL REVIEW RECOMMENDED\n")
            print(f"Commit: {commit_ref[:8]}")
            print(f"Message: {msg}")
            print(f"\nThis commit may require architecture documentation updates.")
            print(f"Please review and update ARCHITECTURE.md if needed.\n")
            sys.exit(2)
        else:
            print(f"✅ No architecture update needed for {commit_ref[:8]}")
            sys.exit(0)


if __name__ == '__main__':
    main()
