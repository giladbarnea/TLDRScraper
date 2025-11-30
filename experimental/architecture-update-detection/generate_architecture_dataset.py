#!/usr/bin/env python3
"""
Generate a dataset of commits for training/evaluating architecture update detection.
Output: JSON file with commit features, labels, and diff summaries.
"""

import subprocess
import json
from pathlib import Path
from collections import defaultdict


def run_git(cmd):
    """Run git command and return output."""
    result = subprocess.run(
        f"git {cmd}",
        shell=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    return result.stdout.strip()


def extract_commit_features(commit_hash):
    """Extract all features from a commit for the dataset."""

    # Basic info
    message_subject = run_git(f"log -1 --format=%s {commit_hash}")
    message_body = run_git(f"log -1 --format=%b {commit_hash}")
    author = run_git(f"log -1 --format=%an {commit_hash}")
    date = run_git(f"log -1 --format=%ai {commit_hash}")

    # Files changed
    files_output = run_git(f"diff-tree --no-commit-id --name-only -r -m --first-parent {commit_hash}")
    files = [f for f in files_output.split('\n') if f]

    # Get numstat for additions/deletions
    numstat = run_git(f"diff-tree --no-commit-id --numstat -r -m --first-parent {commit_hash}")

    # Parse numstat
    total_additions = 0
    total_deletions = 0
    file_stats = {}

    for line in numstat.split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) >= 3:
            added, deleted, filename = parts[0], parts[1], parts[2]
            try:
                added_int = 0 if added == '-' else int(added)
                deleted_int = 0 if deleted == '-' else int(deleted)
                total_additions += added_int
                total_deletions += deleted_int
                file_stats[filename] = {'added': added_int, 'deleted': deleted_int}
            except ValueError:
                pass

    # Check ARCHITECTURE.md changes
    arch_changed = 'ARCHITECTURE.md' in files
    arch_body_changed = False
    arch_frontmatter_only = False

    if arch_changed:
        diff = run_git(f"show {commit_hash} -- ARCHITECTURE.md")
        diff_lines = [l for l in diff.split('\n') if l.startswith('+') or l.startswith('-')]
        diff_lines = [l for l in diff_lines if not l.startswith('+++') and not l.startswith('---')]

        frontmatter_changes = [l for l in diff_lines if 'last_updated' in l]
        non_frontmatter_changes = [l for l in diff_lines if 'last_updated' not in l]

        if frontmatter_changes and not non_frontmatter_changes:
            arch_frontmatter_only = True
        elif non_frontmatter_changes:
            arch_body_changed = True

    # Categorize files
    features = {
        'commit_hash': commit_hash,
        'commit_hash_short': commit_hash[:8],
        'message_subject': message_subject,
        'message_body': message_body,
        'author': author,
        'date': date,
        'total_files_changed': len(files),
        'total_additions': total_additions,
        'total_deletions': total_deletions,
        'files': files,
        'file_stats': file_stats,

        # Architecture labels
        'architecture_changed': arch_changed,
        'architecture_body_changed': arch_body_changed,
        'architecture_frontmatter_only': arch_frontmatter_only,

        # File type counts
        'jsx_components': 0,
        'jsx_non_component': 0,
        'js_hooks': 0,
        'js_lib': 0,
        'css_files': 0,
        'py_core': 0,
        'py_adapters': 0,
        'py_scripts': 0,
        'py_other': 0,
        'md_docs': 0,
        'config_files': 0,
        'test_files': 0,
        'other_files': 0,

        # Specific important files (boolean flags)
        'has_app_jsx': False,
        'has_serve_py': False,
        'has_scraper_js': False,
        'has_storage_api': False,
        'has_supabase_client': False,
        'has_state_hooks': False,

        # Message analysis (boolean flags)
        'msg_feat': False,
        'msg_fix': False,
        'msg_refactor': False,
        'msg_docs': False,
        'msg_chore': False,
        'msg_test': False,
        'msg_new_feature': False,
        'msg_behavior_change': False,
        'msg_flow_change': False,
        'msg_component_change': False,
        'msg_state_change': False,
        'msg_ui_change': False,
        'msg_architecture': False,
    }

    # Categorize files
    for f in files:
        if not f:
            continue

        if f.startswith('client/src/components/') and f.endswith('.jsx'):
            features['jsx_components'] += 1
        elif f.startswith('client/src/hooks/') and f.endswith('.js'):
            features['js_hooks'] += 1
            if any(hook in f for hook in ['useArticleState', 'useSupabaseStorage', 'useSummary', 'useLocalStorage']):
                features['has_state_hooks'] = True
        elif f.startswith('client/src/lib/') and f.endswith('.js'):
            features['js_lib'] += 1
            if 'scraper.js' in f:
                features['has_scraper_js'] = True
            if 'storageApi' in f:
                features['has_storage_api'] = True
        elif f.endswith('.jsx'):
            features['jsx_non_component'] += 1
            if 'App.jsx' in f:
                features['has_app_jsx'] = True
        elif f.endswith('.css'):
            features['css_files'] += 1
        elif f == 'serve.py':
            features['py_core'] += 1
            features['has_serve_py'] = True
        elif f in ['tldr_service.py', 'newsletter_scraper.py', 'tldr_app.py', 'storage_service.py', 'supabase_client.py']:
            features['py_core'] += 1
            if f == 'supabase_client.py':
                features['has_supabase_client'] = True
        elif f.startswith('adapters/') or f.endswith('_adapter.py'):
            features['py_adapters'] += 1
        elif f.startswith('scripts/') and f.endswith('.py'):
            features['py_scripts'] += 1
        elif f.endswith('.py'):
            features['py_other'] += 1
        elif f.endswith('.md') and f != 'ARCHITECTURE.md':
            features['md_docs'] += 1
        elif f.startswith('tests/') or 'test_' in f:
            features['test_files'] += 1
        elif any(x in f for x in ['package.json', 'package-lock.json', 'vite.config', 'vercel.json',
                                   '.yml', '.yaml', '.githooks', '.github', 'pyproject.toml', 'uv.lock']):
            features['config_files'] += 1
        else:
            features['other_files'] += 1

    # Analyze message
    msg_lower = (message_subject + ' ' + message_body).lower()

    # Conventional commit types
    features['msg_feat'] = msg_lower.startswith('feat:') or msg_lower.startswith('feature:')
    features['msg_fix'] = msg_lower.startswith('fix:')
    features['msg_refactor'] = msg_lower.startswith('refactor:')
    features['msg_docs'] = msg_lower.startswith('docs:')
    features['msg_chore'] = msg_lower.startswith('chore:')
    features['msg_test'] = msg_lower.startswith('test:')

    # Semantic keywords
    features['msg_new_feature'] = any(kw in msg_lower for kw in ['feat:', 'feature:', 'add new', 'new feature', 'implement'])
    features['msg_behavior_change'] = any(kw in msg_lower for kw in
        ['behavior', 'behaviour', 'change how', 'now', 'instead', 'auto-fold', 'auto-collapse',
         'reposition', 'sort', 'deprioritize', 'move to'])
    features['msg_flow_change'] = any(kw in msg_lower for kw in
        ['flow', 'interaction', 'user', 'click', 'when user', 'on click'])
    features['msg_component_change'] = any(kw in msg_lower for kw in
        ['component', 'jsx', 'container', 'layout', 'render'])
    features['msg_state_change'] = any(kw in msg_lower for kw in
        ['state', 'hook', 'reactive', 'storage', 'cache', 'persist'])
    features['msg_ui_change'] = any(kw in msg_lower for kw in
        ['ui', 'display', 'show', 'hide', 'visible', 'button', 'icon'])
    features['msg_architecture'] = any(kw in msg_lower for kw in
        ['architecture', 'structure', 'design', 'pattern', 'system'])

    return features


def detect_retrospective_labels(commits_data):
    """
    Detect commits that should have updated architecture (retrospectively).

    Heuristic: If commit N changed components/hooks and commit N+1 or N+2
    updated ARCHITECTURE.md, label N as "should_have_updated: true".
    """
    # Sort by date (newest first, since git log returns that way)
    commits = sorted(commits_data, key=lambda x: x['date'], reverse=True)

    for i, commit in enumerate(commits):
        # Initialize retrospective fields
        commit['should_have_updated'] = None  # None = unknown, True/False = labeled
        commit['updated_in_later_commit'] = None
        commit['commits_until_update'] = None

        # Skip if architecture was already updated in this commit
        if commit['architecture_body_changed']:
            commit['should_have_updated'] = False  # Already updated, no need
            continue

        # Look at next few commits (N+1 to N+3)
        for j in range(i + 1, min(i + 4, len(commits))):
            later_commit = commits[j]

            # Check if later commit updated architecture body
            # (more lenient - just check if architecture was updated)
            if later_commit['architecture_body_changed']:
                # Check if current commit had component/hook changes that might warrant update
                has_meaningful_changes = (
                    commit['jsx_components'] > 0 or
                    commit['js_hooks'] > 0 or
                    commit['msg_behavior_change'] or
                    commit['msg_component_change']
                )

                if has_meaningful_changes:
                    # This commit likely should have updated architecture
                    commit['should_have_updated'] = True
                    commit['updated_in_later_commit'] = later_commit['commit_hash_short']
                    commit['commits_until_update'] = j - i
                    break

        # If we didn't find a later update, leave as None (unknown)
        if commit['should_have_updated'] is None:
            # If commit changed components/hooks but no later doc update found,
            # we can't definitively say it should/shouldn't have updated
            pass

    return commits


def generate_dataset(limit=200):
    """Generate full dataset of commits."""
    print(f"Fetching commits (limit={limit})...")

    # Get merge commits
    merge_commits = run_git(f"log --merges --first-parent --format=%H -n {limit}").split('\n')
    # Get PR squash commits
    squash_commits = run_git(f"log --first-parent --format=%H --grep='(#[0-9]' -n {limit}").split('\n')

    all_commits = list(set(c for c in merge_commits + squash_commits if c))
    print(f"Found {len(all_commits)} unique commits")

    dataset = []

    for i, commit in enumerate(all_commits):
        if i % 10 == 0:
            print(f"Processing commit {i+1}/{len(all_commits)}...")

        features = extract_commit_features(commit)
        dataset.append(features)

    # Detect retrospective labels
    print("\nDetecting retrospective labels...")
    dataset = detect_retrospective_labels(dataset)

    # Create summary statistics
    arch_updated = [c for c in dataset if c['architecture_body_changed']]
    arch_not_updated = [c for c in dataset if not c['architecture_body_changed'] and not c['architecture_frontmatter_only']]
    should_have_updated = [c for c in dataset if c.get('should_have_updated') is True]

    summary = {
        'total_commits': len(dataset),
        'architecture_body_updated': len(arch_updated),
        'architecture_not_updated': len(arch_not_updated),
        'architecture_frontmatter_only': sum(1 for c in dataset if c['architecture_frontmatter_only']),
        'retrospective_should_have_updated': len(should_have_updated),
    }

    print(f"\nDataset Summary:")
    print(f"  Total commits: {summary['total_commits']}")
    print(f"  Architecture body updated: {summary['architecture_body_updated']}")
    print(f"  Architecture not updated: {summary['architecture_not_updated']}")
    print(f"  Frontmatter only: {summary['architecture_frontmatter_only']}")
    print(f"  Retrospectively labeled as should-have-updated: {summary['retrospective_should_have_updated']}")

    return {
        'summary': summary,
        'commits': dataset
    }


if __name__ == '__main__':
    dataset = generate_dataset(limit=200)

    # Save to JSON
    output_file = Path(__file__).parent / 'architecture_update_dataset.json'
    with open(output_file, 'w') as f:
        json.dump(dataset, f, indent=2)

    print(f"\nDataset saved to: {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024:.1f} KB")

    # Also save a "training ready" version with just the features needed for ML
    training_features = []
    for commit in dataset['commits']:
        # Skip frontmatter-only commits
        if commit['architecture_frontmatter_only']:
            continue

        # Determine label
        if commit['architecture_body_changed']:
            label = 1  # Updated in this commit
        elif commit.get('should_have_updated') is True:
            label = 1  # Should have updated (retrospective)
        else:
            label = 0  # No update needed

        training_features.append({
            'commit': commit['commit_hash_short'],
            'message': commit['message_subject'],
            'label': label,
            'features': {
                k: v for k, v in commit.items()
                if k.startswith(('jsx_', 'js_', 'css_', 'py_', 'md_', 'config_', 'test_',
                                'has_', 'msg_', 'total_'))
                and k not in ['total_files_changed']  # Redundant with individual counts
            }
        })

    training_file = Path(__file__).parent / 'architecture_update_training.json'
    with open(training_file, 'w') as f:
        json.dump(training_features, f, indent=2)

    print(f"Training dataset saved to: {training_file}")
    print(f"Training examples: {len(training_features)}")
    print(f"  Positive examples (label=1): {sum(1 for x in training_features if x['label'] == 1)}")
    print(f"  Negative examples (label=0): {sum(1 for x in training_features if x['label'] == 0)}")
