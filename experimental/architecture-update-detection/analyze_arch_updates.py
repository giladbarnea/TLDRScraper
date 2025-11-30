#!/usr/bin/env python3
"""
Analyze git history to determine when ARCHITECTURE.md should be updated.
Groups merges by whether ARCHITECTURE.md body was updated or not.
"""

import subprocess
import re
from collections import defaultdict
import json

def run_git(cmd):
    """Run git command and return output."""
    result = subprocess.run(
        f"git {cmd}",
        shell=True,
        capture_output=True,
        text=True,
        cwd="/home/user/TLDRScraper"
    )
    return result.stdout.strip()

def get_merge_commits(limit=200):
    """Get list of merge commit hashes."""
    output = run_git(f"log --merges --first-parent --format=%H -n {limit}")
    return output.split('\n') if output else []

def get_pr_squash_commits(limit=200):
    """Get commits that look like PR squashes (contain PR number in message)."""
    output = run_git(f"log --first-parent --format=%H --grep='(#[0-9]' -n {limit}")
    return output.split('\n') if output else []

def get_commit_info(commit_hash):
    """Get detailed info about a commit."""
    # Get commit message
    message = run_git(f"log -1 --format=%s {commit_hash}")

    # Get files changed - for merge commits, compare against first parent
    # This shows what actually changed when the PR was merged
    files = run_git(f"diff-tree --no-commit-id --name-only -r -m --first-parent {commit_hash}")
    files_list = files.split('\n') if files else []

    # Get detailed diff for ARCHITECTURE.md if it was changed
    arch_changed = 'ARCHITECTURE.md' in files_list
    arch_body_changed = False
    arch_frontmatter_only = False

    if arch_changed:
        diff = run_git(f"show {commit_hash} -- ARCHITECTURE.md")
        # Check if only frontmatter changed (lines starting with last_updated)
        diff_lines = [l for l in diff.split('\n') if l.startswith('+') or l.startswith('-')]
        diff_lines = [l for l in diff_lines if not l.startswith('+++') and not l.startswith('---')]

        frontmatter_changes = [l for l in diff_lines if 'last_updated' in l]
        non_frontmatter_changes = [l for l in diff_lines if 'last_updated' not in l]

        if frontmatter_changes and not non_frontmatter_changes:
            arch_frontmatter_only = True
        elif non_frontmatter_changes:
            arch_body_changed = True

    # Get stats
    stats = run_git(f"diff-tree --no-commit-id --numstat {commit_hash}")

    return {
        'hash': commit_hash,
        'message': message,
        'files': files_list,
        'arch_changed': arch_changed,
        'arch_body_changed': arch_body_changed,
        'arch_frontmatter_only': arch_frontmatter_only,
        'stats': stats
    }

def categorize_files(files):
    """Categorize changed files by type."""
    categories = {
        'client_jsx': [],
        'client_js': [],
        'client_css': [],
        'client_hooks': [],
        'client_components': [],
        'server_py': [],
        'adapters': [],
        'docs': [],
        'config': [],
        'tests': [],
        'other': []
    }

    for f in files:
        if not f:
            continue
        if f.startswith('client/src/components/'):
            categories['client_components'].append(f)
        elif f.startswith('client/src/hooks/'):
            categories['client_hooks'].append(f)
        elif f.endswith('.jsx'):
            categories['client_jsx'].append(f)
        elif f.endswith('.js') and 'client' in f:
            categories['client_js'].append(f)
        elif f.endswith('.css'):
            categories['client_css'].append(f)
        elif f.endswith('.py') and not f.startswith('adapters/'):
            categories['server_py'].append(f)
        elif f.startswith('adapters/'):
            categories['adapters'].append(f)
        elif f.endswith('.md') or f.startswith('docs/'):
            categories['docs'].append(f)
        elif f.startswith('tests/'):
            categories['tests'].append(f)
        elif 'config' in f or f.endswith('.json') or f.endswith('.yml'):
            categories['config'].append(f)
        else:
            categories['other'].append(f)

    return categories

def analyze_commits():
    """Analyze all merge commits and categorize by ARCHITECTURE.md updates."""
    print("Fetching merge commits...")
    merge_commits = get_merge_commits(100)
    squash_commits = get_pr_squash_commits(100)

    all_commits = list(set(merge_commits + squash_commits))
    print(f"Found {len(all_commits)} commits to analyze")

    arch_updated = []
    arch_not_updated = []

    for i, commit in enumerate(all_commits):
        if i % 10 == 0:
            print(f"Processing commit {i+1}/{len(all_commits)}...")

        info = get_commit_info(commit)

        # Skip if only frontmatter changed
        if info['arch_frontmatter_only']:
            continue

        # Categorize files
        categories = categorize_files(info['files'])
        info['categories'] = categories

        # Group by whether architecture body was updated
        if info['arch_body_changed']:
            arch_updated.append(info)
        else:
            arch_not_updated.append(info)

    print(f"\nARCHITECTURE.md body updated: {len(arch_updated)} commits")
    print(f"ARCHITECTURE.md body NOT updated: {len(arch_not_updated)} commits")

    return arch_updated, arch_not_updated

def print_analysis(arch_updated, arch_not_updated):
    """Print analysis of both groups."""

    print("\n" + "="*80)
    print("COMMITS WHERE ARCHITECTURE.MD BODY WAS UPDATED")
    print("="*80)
    for info in arch_updated[:20]:  # Show first 20
        print(f"\n{info['hash'][:8]}: {info['message']}")
        cats = info['categories']
        print(f"  Client components: {len(cats['client_components'])}")
        print(f"  Client hooks: {len(cats['client_hooks'])}")
        print(f"  Server Python: {len(cats['server_py'])}")
        print(f"  Docs: {len(cats['docs'])}")
        if cats['client_components']:
            print(f"    Components: {', '.join([f.split('/')[-1] for f in cats['client_components']])}")
        if cats['server_py']:
            print(f"    Server files: {', '.join([f.split('/')[-1] for f in cats['server_py']])}")

    print("\n" + "="*80)
    print("COMMITS WHERE ARCHITECTURE.MD BODY WAS *NOT* UPDATED")
    print("="*80)
    for info in arch_not_updated[:30]:  # Show first 30
        print(f"\n{info['hash'][:8]}: {info['message']}")
        cats = info['categories']
        print(f"  Client components: {len(cats['client_components'])}")
        print(f"  Client hooks: {len(cats['client_hooks'])}")
        print(f"  Server Python: {len(cats['server_py'])}")
        print(f"  Adapters: {len(cats['adapters'])}")
        print(f"  Docs: {len(cats['docs'])}")
        print(f"  Tests: {len(cats['tests'])}")
        print(f"  Config: {len(cats['config'])}")
        if cats['client_components']:
            print(f"    Components: {', '.join([f.split('/')[-1] for f in cats['client_components']])}")
        if cats['server_py']:
            print(f"    Server files: {', '.join([f.split('/')[-1] for f in cats['server_py']])}")
        if cats['adapters']:
            print(f"    Adapters: {', '.join([f.split('/')[-1] for f in cats['adapters']])}")

def analyze_commit_messages(commits, label):
    """Analyze commit messages for keywords."""
    print(f"\n{label} - COMMIT MESSAGE KEYWORDS:")
    keywords = defaultdict(int)
    keyword_list = [
        'feat', 'fix', 'refactor', 'docs', 'style', 'test', 'chore',
        'add', 'remove', 'update', 'improve', 'implement',
        'state', 'component', 'hook', 'api', 'endpoint', 'flow',
        'UI', 'frontend', 'backend', 'server', 'client',
        'cache', 'storage', 'database', 'supabase',
        'architecture', 'structure', 'design', 'pattern'
    ]

    for info in commits:
        msg = info['message'].lower()
        for keyword in keyword_list:
            if keyword.lower() in msg:
                keywords[keyword] += 1

    # Sort by frequency
    sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
    for keyword, count in sorted_keywords[:15]:
        pct = (count / len(commits)) * 100 if commits else 0
        print(f"  {keyword}: {count} ({pct:.1f}%)")

def find_patterns(arch_updated, arch_not_updated):
    """Identify patterns that distinguish the two groups."""
    print("\n" + "="*80)
    print("PATTERN ANALYSIS")
    print("="*80)

    # Analyze commit messages
    analyze_commit_messages(arch_updated, "ARCHITECTURE UPDATED")
    analyze_commit_messages(arch_not_updated, "ARCHITECTURE NOT UPDATED")

    # Aggregate stats for each group
    def aggregate_stats(commits):
        stats = {
            'total_commits': len(commits),
            'avg_files_changed': 0,
            'avg_client_components': 0,
            'avg_client_hooks': 0,
            'avg_server_py': 0,
            'avg_adapters': 0,
            'has_serve_py': 0,
            'has_tldr_service': 0,
            'has_newsletter_scraper': 0,
            'has_new_components': 0,
            'has_state_management_changes': 0,
        }

        for info in commits:
            stats['avg_files_changed'] += len(info['files'])
            cats = info['categories']
            stats['avg_client_components'] += len(cats['client_components'])
            stats['avg_client_hooks'] += len(cats['client_hooks'])
            stats['avg_server_py'] += len(cats['server_py'])
            stats['avg_adapters'] += len(cats['adapters'])

            # Check for specific files
            if 'serve.py' in info['files']:
                stats['has_serve_py'] += 1
            if 'tldr_service.py' in info['files']:
                stats['has_tldr_service'] += 1
            if 'newsletter_scraper.py' in info['files']:
                stats['has_newsletter_scraper'] += 1

            # Check for new components (additions)
            if any('new file' in info['stats'].lower() or '+' in info['stats'] for f in cats['client_components']):
                stats['has_new_components'] += 1

            # Check for state management changes
            state_files = ['useArticleState.js', 'useSupabaseStorage.js', 'useSummary.js', 'useLocalStorage.js']
            if any(f in info['files'] for f in state_files):
                stats['has_state_management_changes'] += 1

        # Calculate averages
        if stats['total_commits'] > 0:
            for key in ['avg_files_changed', 'avg_client_components', 'avg_client_hooks',
                       'avg_server_py', 'avg_adapters']:
                stats[key] = stats[key] / stats['total_commits']

        return stats

    updated_stats = aggregate_stats(arch_updated)
    not_updated_stats = aggregate_stats(arch_not_updated)

    print("\nWHEN ARCHITECTURE.MD WAS UPDATED:")
    for key, val in updated_stats.items():
        print(f"  {key}: {val:.2f}" if isinstance(val, float) else f"  {key}: {val}")

    print("\nWHEN ARCHITECTURE.MD WAS NOT UPDATED:")
    for key, val in not_updated_stats.items():
        print(f"  {key}: {val:.2f}" if isinstance(val, float) else f"  {key}: {val}")

    print("\n" + "="*80)
    print("KEY DIFFERENCES (updated vs not updated):")
    print("="*80)
    print(f"Avg files changed: {updated_stats['avg_files_changed']:.2f} vs {not_updated_stats['avg_files_changed']:.2f}")
    print(f"Avg client components: {updated_stats['avg_client_components']:.2f} vs {not_updated_stats['avg_client_components']:.2f}")
    print(f"Avg server Python files: {updated_stats['avg_server_py']:.2f} vs {not_updated_stats['avg_server_py']:.2f}")
    print(f"serve.py changes: {updated_stats['has_serve_py']} vs {not_updated_stats['has_serve_py']}")
    print(f"State management changes: {updated_stats['has_state_management_changes']} vs {not_updated_stats['has_state_management_changes']}")

if __name__ == "__main__":
    arch_updated, arch_not_updated = analyze_commits()
    print_analysis(arch_updated, arch_not_updated)
    find_patterns(arch_updated, arch_not_updated)
