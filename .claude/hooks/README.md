# Two-Layer Blocking Hook

PreToolUse hook enforcing path-based interaction before allowing tool use.

## Mechanism

**Layer 1**: Block all tools until ANY interaction with `setup.sh`
**Layer 2**: Block all tools until ANY interaction with `.claude/skills/catchup*`

Tracking file: `/tmp/claude-blocking-state.json`
```json
{"setup_sh_interacted": false, "catchup_skill_interacted": false}
```

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
