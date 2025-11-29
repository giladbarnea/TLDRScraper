---
last_updated: 2025-11-17 11:33, 6743fd6
---
# Syncing Upstream Architecture Commands

## Git Subtree for Selective Sync

To automatically sync architecture slash commands from `giladbarnea/.claude` repository without maintaining a full submodule:

### One-time Setup

Add the remote repository as a subtree, syncing only specific files into `.claude/commands/architecture`:

```bash
git subtree add --prefix=.claude/commands/architecture \
  https://github.com/giladbarnea/.claude.git main --squash
```

### Updating from Upstream

Pull changes from the upstream repository:

```bash
git subtree pull --prefix=.claude/commands/architecture \
  https://github.com/giladbarnea/.claude.git main --squash
```

### Benefits

- Files are committed directly to your repository (no submodule complexity)
- Works seamlessly with `git clone` (no extra setup needed)
- Can make local modifications easily
- History is squashed, keeping the repository clean
- Updates are explicit and controlled

### Making Local Customizations

After syncing, you can modify the files locally:

```bash
# Edit files in .claude/commands/architecture/
vim .claude/commands/architecture/architecture_create.md

# Commit your local changes
git commit -m "feat: Customize architecture_create.md for TLDRScraper project"
```

When pulling upstream updates later, git will merge upstream changes with your local modifications (conflicts may need manual resolution).
