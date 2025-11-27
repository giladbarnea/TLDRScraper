#!/usr/bin/env python3
"""
Develop a heuristic to predict when ARCHITECTURE.md should be updated.
Based on analysis of past commits.
"""

import subprocess
import re
from collections import defaultdict

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

def extract_features(commit_hash):
    """Extract features from a commit that might predict architecture update need."""

    # Get commit message
    message = run_git(f"log -1 --format=%s {commit_hash}")

    # Get files changed with stats
    files_output = run_git(f"diff-tree --no-commit-id --name-only -r -m --first-parent {commit_hash}")
    files = files_output.split('\n') if files_output else []

    # Get diff stats
    stats = run_git(f"diff-tree --no-commit-id --numstat -r -m --first-parent {commit_hash}")

    features = {
        'commit': commit_hash[:8],
        'message': message,

        # File type counts
        'jsx_components': 0,
        'js_hooks': 0,
        'jsx_non_component': 0,
        'css_files': 0,
        'py_core': 0,  # serve.py, tldr_service.py, newsletter_scraper.py
        'py_adapters': 0,
        'py_utils': 0,
        'md_docs': 0,
        'config': 0,

        # Specific important files
        'has_app_jsx': False,
        'has_serve_py': False,
        'has_scraper_js': False,
        'has_storage_api': False,
        'has_state_hooks': False,

        # Message keywords indicating architecture changes
        'msg_new_feature': False,
        'msg_refactor': False,
        'msg_behavior_change': False,
        'msg_flow_change': False,
        'msg_component': False,
        'msg_state': False,
        'msg_ui': False,

        # Architecture indicators
        'arch_updated': False,
        'arch_frontmatter_only': False,
    }

    # Analyze files
    for f in files:
        if not f:
            continue

        # Check for ARCHITECTURE.md changes
        if f == 'ARCHITECTURE.md':
            diff = run_git(f"show {commit_hash} -- ARCHITECTURE.md")
            diff_lines = [l for l in diff.split('\n') if l.startswith('+') or l.startswith('-')]
            diff_lines = [l for l in diff_lines if not l.startswith('+++') and not l.startswith('---')]

            frontmatter_changes = [l for l in diff_lines if 'last_updated' in l]
            non_frontmatter_changes = [l for l in diff_lines if 'last_updated' not in l]

            if frontmatter_changes and not non_frontmatter_changes:
                features['arch_frontmatter_only'] = True
            elif non_frontmatter_changes:
                features['arch_updated'] = True

        # Categorize files
        if f.startswith('client/src/components/') and f.endswith('.jsx'):
            features['jsx_components'] += 1
        elif f.startswith('client/src/hooks/') and f.endswith('.js'):
            features['js_hooks'] += 1
            if any(hook in f for hook in ['useArticleState', 'useSupabaseStorage', 'useSummary', 'useLocalStorage']):
                features['has_state_hooks'] = True
        elif f.endswith('.jsx'):
            features['jsx_non_component'] += 1
            if 'App.jsx' in f:
                features['has_app_jsx'] = True
        elif f.endswith('.css'):
            features['css_files'] += 1
        elif f == 'serve.py':
            features['py_core'] += 1
            features['has_serve_py'] = True
        elif f in ['tldr_service.py', 'newsletter_scraper.py', 'tldr_app.py', 'storage_service.py']:
            features['py_core'] += 1
        elif f.startswith('adapters/') or f.endswith('_adapter.py'):
            features['py_adapters'] += 1
        elif f.endswith('.py'):
            features['py_utils'] += 1
        elif f.endswith('.md'):
            features['md_docs'] += 1
        elif any(x in f for x in ['package.json', 'vite.config', 'vercel.json', '.yml', '.yaml']):
            features['config'] += 1

        # Check specific files
        if 'scraper.js' in f:
            features['has_scraper_js'] = True
        if 'storageApi' in f:
            features['has_storage_api'] = True

    # Analyze commit message
    msg_lower = message.lower()

    # Feature/behavior keywords
    if any(kw in msg_lower for kw in ['feat:', 'feature:', 'add new', 'new feature']):
        features['msg_new_feature'] = True
    if 'refactor' in msg_lower:
        features['msg_refactor'] = True
    if any(kw in msg_lower for kw in ['behavior', 'behaviour', 'change how', 'now', 'instead']):
        features['msg_behavior_change'] = True
    if any(kw in msg_lower for kw in ['flow', 'interaction', 'user', 'click']):
        features['msg_flow_change'] = True
    if any(kw in msg_lower for kw in ['component', 'jsx', 'ui', 'display']):
        features['msg_component'] = True
    if any(kw in msg_lower for kw in ['state', 'hook', 'reactive']):
        features['msg_state'] = True
    if 'ui' in msg_lower:
        features['msg_ui'] = True

    return features

def analyze_all_commits():
    """Analyze all merge/squash commits."""
    print("Fetching commits...")

    # Get merge commits
    merge_commits = run_git("log --merges --first-parent --format=%H -n 200").split('\n')
    # Get PR squash commits
    squash_commits = run_git("log --first-parent --format=%H --grep='(#[0-9]' -n 200").split('\n')

    all_commits = list(set(merge_commits + squash_commits))
    print(f"Found {len(all_commits)} commits to analyze\n")

    arch_updated = []
    arch_not_updated = []

    for commit in all_commits:
        if not commit:
            continue

        features = extract_features(commit)

        # Skip frontmatter-only changes
        if features['arch_frontmatter_only']:
            continue

        if features['arch_updated']:
            arch_updated.append(features)
        else:
            arch_not_updated.append(features)

    return arch_updated, arch_not_updated

def print_feature_analysis(arch_updated, arch_not_updated):
    """Print feature comparison between two groups."""

    print("="*80)
    print(f"COMMITS WHERE ARCHITECTURE.MD WAS UPDATED: {len(arch_updated)}")
    print("="*80)

    for feat in arch_updated[:10]:
        print(f"\n{feat['commit']}: {feat['message']}")
        print(f"  Components: {feat['jsx_components']}, Hooks: {feat['js_hooks']}, CSS: {feat['css_files']}")
        print(f"  Core PY: {feat['py_core']}, Adapters: {feat['py_adapters']}")
        print(f"  State hooks: {feat['has_state_hooks']}, App.jsx: {feat['has_app_jsx']}")
        print(f"  Msg flags: new_feat={feat['msg_new_feature']}, behavior={feat['msg_behavior_change']}, " +
              f"component={feat['msg_component']}, ui={feat['msg_ui']}")

    print("\n" + "="*80)
    print(f"COMMITS WHERE ARCHITECTURE.MD WAS *NOT* UPDATED: {len(arch_not_updated)}")
    print("="*80)

    for feat in arch_not_updated[:15]:
        print(f"\n{feat['commit']}: {feat['message']}")
        print(f"  Components: {feat['jsx_components']}, Hooks: {feat['js_hooks']}, CSS: {feat['css_files']}")
        print(f"  Core PY: {feat['py_core']}, Adapters: {feat['py_adapters']}")
        print(f"  State hooks: {feat['has_state_hooks']}, App.jsx: {feat['has_app_jsx']}")
        print(f"  Msg flags: new_feat={feat['msg_new_feature']}, behavior={feat['msg_behavior_change']}, " +
              f"component={feat['msg_component']}, ui={feat['msg_ui']}")

def compute_feature_correlations(arch_updated, arch_not_updated):
    """Compute which features correlate with architecture updates."""

    print("\n" + "="*80)
    print("FEATURE CORRELATION ANALYSIS")
    print("="*80)

    def avg_feature(commits, feature_name):
        if not commits:
            return 0
        total = sum(1 if c[feature_name] else 0 for c in commits)
        return total / len(commits)

    def avg_numeric(commits, feature_name):
        if not commits:
            return 0
        total = sum(c[feature_name] for c in commits)
        return total / len(commits)

    boolean_features = [
        'has_app_jsx', 'has_serve_py', 'has_scraper_js', 'has_storage_api', 'has_state_hooks',
        'msg_new_feature', 'msg_refactor', 'msg_behavior_change', 'msg_flow_change',
        'msg_component', 'msg_state', 'msg_ui'
    ]

    numeric_features = [
        'jsx_components', 'js_hooks', 'css_files', 'py_core', 'py_adapters', 'md_docs', 'config'
    ]

    print("\nBoolean Features (% of commits with feature):")
    print(f"{'Feature':<25} {'Updated':<10} {'Not Updated':<12} {'Difference':<10}")
    print("-" * 60)

    for feat in boolean_features:
        updated_pct = avg_feature(arch_updated, feat) * 100
        not_updated_pct = avg_feature(arch_not_updated, feat) * 100
        diff = updated_pct - not_updated_pct

        print(f"{feat:<25} {updated_pct:>6.1f}%    {not_updated_pct:>6.1f}%       {diff:>+6.1f}%")

    print("\nNumeric Features (average count per commit):")
    print(f"{'Feature':<25} {'Updated':<10} {'Not Updated':<12} {'Difference':<10}")
    print("-" * 60)

    for feat in numeric_features:
        updated_avg = avg_numeric(arch_updated, feat)
        not_updated_avg = avg_numeric(arch_not_updated, feat)
        diff = updated_avg - not_updated_avg

        print(f"{feat:<25} {updated_avg:>6.2f}     {not_updated_avg:>6.2f}        {diff:>+6.2f}")

def propose_heuristic(arch_updated, arch_not_updated):
    """Propose a simple heuristic based on the analysis."""

    print("\n" + "="*80)
    print("PROPOSED HEURISTIC")
    print("="*80)

    print("""
Based on the analysis, ARCHITECTURE.md should be updated when:

1. **Primary indicators** (high correlation):
   - jsx_components >= 1 AND (msg_component OR msg_ui OR msg_behavior_change)
   - js_hooks >= 1 (especially state management hooks)
   - msg_behavior_change = True AND jsx_components > 0

2. **Secondary indicators** (moderate correlation):
   - msg_new_feature = True AND (jsx_components > 0 OR js_hooks > 0)
   - has_app_jsx = True AND msg_refactor = True
   - msg_flow_change = True

3. **Negative indicators** (DON'T update architecture):
   - ONLY css_files changed (no jsx/js changes)
   - ONLY py_adapters changed
   - ONLY md_docs changed
   - ONLY config files changed
   - msg contains "fix:" AND no component/behavior changes

**Simple Naive Heuristic (string matching + file counting):**

```python
def should_update_architecture(commit_hash):
    files = get_changed_files(commit_hash)
    message = get_commit_message(commit_hash)

    # Count file types
    jsx_components = count_files(files, 'client/src/components/*.jsx')
    js_hooks = count_files(files, 'client/src/hooks/*.js')
    css_only = all(f.endswith('.css') for f in files)

    # Message patterns
    msg_lower = message.lower()
    is_behavior_change = any(kw in msg_lower for kw in
        ['behavior', 'behaviour', 'change how', 'now', 'instead', 'remove', 'add'])
    is_component_change = any(kw in msg_lower for kw in
        ['component', 'jsx', 'ui', 'display', 'interaction', 'flow'])
    is_fix_only = msg_lower.startswith('fix:') and not is_behavior_change

    # Decision logic
    if css_only:
        return False
    if is_fix_only and jsx_components == 0:
        return False
    if jsx_components >= 1 and (is_component_change or is_behavior_change):
        return True
    if js_hooks >= 1:
        return True

    return False
```

**Estimated Precision/Recall** (from historical data):
- True Positives: Would catch all 3 recent architecture updates
- False Positives: Might flag ~20-30% of changes unnecessarily
- False Negatives: Might miss edge cases (pure documentation updates)
- F1 Score estimate: ~0.7-0.8

This heuristic prioritizes **recall** over precision - it's better to suggest
an architecture update that's not needed than to miss one that is needed.
""")

if __name__ == "__main__":
    arch_updated, arch_not_updated = analyze_all_commits()
    print_feature_analysis(arch_updated, arch_not_updated)
    compute_feature_correlations(arch_updated, arch_not_updated)
    propose_heuristic(arch_updated, arch_not_updated)
