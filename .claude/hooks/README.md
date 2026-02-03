---
last_updated: 2026-02-03 06:49, 0f84214
---
# Two-Layer Blocking Hook

PreToolUse hook enforcing path-based interaction before allowing tool use.

## Mechanism

**Layer 1**: Block all tools until ANY interaction with `setup.sh`
**Layer 2**: Block all tools until ANY interaction with `.claude/skills/catchup*`

Tracking file: `/tmp/claude-blocking-state.json`
```json
{"setup_sh_interacted": false, "catchup_skill_interacted": false}
```

Notes:
- Blocking is only active while the tracking file exists.
- The hook counts any tool input that references the paths (e.g. `Read`/`Edit` file paths, `Glob` patterns, `Grep` paths, `Bash` commands containing the path).

## Usage

Enable:
```bash
.claude/hooks/require-reads.sh
```

Disable:
```bash
.claude/hooks/require-reads.sh --clear
```

## Files

- `block-until-reads.sh` - PreToolUse hook (configured in `.claude/settings.json`)
- `require-reads.sh` - Initialize/clear blocking state
