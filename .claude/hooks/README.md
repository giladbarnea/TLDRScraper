# Claude Code Hooks - Two-Layer Blocking System

This directory contains a PreToolUse hook that enforces a two-layer blocking system for proper project context gathering.

## What It Does

The `block-until-reads.sh` hook implements a **two-layer blocking system**:

### Layer 1: Setup Requirement
Blocks **ALL tools** (including Read) until `setup.sh` has been run. This ensures:
- Dependencies are installed
- Client is built
- Environment is verified
- Documentation is generated

### Layer 2: Required File Reads
After setup, blocks all tools **except Read** until specific files are read. This ensures:
- **Context enforcement**: Agents understand architecture before modifying code
- **Safety**: Conventions/guidelines are read before writing code
- **Onboarding**: Critical docs are read before making changes

## How It Works

### Layer 1: Setup Check
1. **Setup flag**: Checks for `$HOME/.cache/tech-news-scraper/setup-complete`
2. If flag doesn't exist → **BLOCK ALL TOOLS** with message to run `./setup.sh`
3. If flag exists → Proceed to Layer 2

### Layer 2: File Read Check
1. **Tracking file**: `/tmp/claude-required-reads.json` tracks which files have been read
2. **PreToolUse hook**: Fires before every tool execution
3. **Blocking logic**:
   - If tracking file exists and not all files are read → **BLOCK** all tools except Read (for required files)
   - When Claude uses Read on a required file → Mark as read and allow
   - Once all files are read → Remove tracking file, resume normal behavior

## Files

- **`block-until-reads.sh`**: The PreToolUse hook script that blocks tool execution
- **`require-reads.sh`**: Helper script to set up required file reads
- **Configuration**: Added to `.claude/settings.json` under `hooks.PreToolUse`

## Usage

### Quick Start: Catchup Files

The easiest way to enforce the catchup skill files (README.md, CLAUDE.md, ARCHITECTURE.md, PROJECT_STRUCTURE.md):

```bash
.claude/hooks/require-reads.sh --catchup

# Output:
# Setting up catchup skill required reads...
# ✓ Required reads tracking initialized at: /tmp/claude-required-reads.json
#
# The following files must be read before Claude can use other tools:
#   - /home/user/TLDRScraper/README.md
#   - /home/user/TLDRScraper/CLAUDE.md
#   - /home/user/TLDRScraper/ARCHITECTURE.md
#   - /home/user/TLDRScraper/PROJECT_STRUCTURE.md
```

### Setting Up Custom Required Reads

```bash
# Require Claude to read these files before proceeding
.claude/hooks/require-reads.sh \
  ./ARCHITECTURE.md \
  ./PROJECT_STRUCTURE.md \
  ./CLAUDE.md

# Output:
# ✓ Required reads tracking initialized at: /tmp/claude-required-reads.json
#
# The following files must be read before Claude can use other tools:
#   - /home/user/TLDRScraper/ARCHITECTURE.md
#   - /home/user/TLDRScraper/PROJECT_STRUCTURE.md
#   - /home/user/TLDRScraper/CLAUDE.md
```

### Clearing the Restriction

```bash
# Remove the tracking file and resume normal behavior
.claude/hooks/require-reads.sh --clear

# Output:
# ✓ Cleared required reads tracking
```

### What Happens When Blocked

#### Layer 1: Setup Not Run

If `setup.sh` hasn't been run, **ALL tools** (including Read) are blocked:

```
🚫 Setup required before any tool use.

Please run setup.sh first:
  source ./setup.sh

Or if in a non-interactive shell:
  ./setup.sh --quiet

This installs dependencies, builds the client, and prepares the environment.
After setup completes, you can proceed with tool operations.
```

#### Layer 2: Required Files Not Read

After setup, when you try to use any tool (Edit, Write, Bash, Glob, etc.) before reading required files:

```
⛔ Required files must be read before proceeding.

Please read these files first:
  - /home/user/TLDRScraper/README.md
  - /home/user/TLDRScraper/CLAUDE.md
  - /home/user/TLDRScraper/ARCHITECTURE.md
  - /home/user/TLDRScraper/PROJECT_STRUCTURE.md

Use the Read tool to read each file, then you can proceed with other operations.
```

Claude can only use the **Read** tool on the required files. Once all files are read, the restriction is lifted automatically.

## Example Workflow

### Two-Layer Context Gathering

```bash
# 1. Start fresh session - setup.sh NOT run yet
# Claude tries any tool → BLOCKED (Layer 1)
# Message: "🚫 Setup required before any tool use..."

# 2. Run setup.sh
source ./setup.sh
# Setup installs dependencies, builds client, writes flag file

# 3. Set up required reads for catchup
.claude/hooks/require-reads.sh --catchup

# 4. Start working - Claude tries to Edit/Write → BLOCKED (Layer 2)
# Message: "⛔ Required files must be read before proceeding..."

# 5. Claude reads required files
# [Reads README.md]
# [Reads CLAUDE.md]
# [Reads ARCHITECTURE.md]
# [Reads PROJECT_STRUCTURE.md]

# 6. All files read - tracking file auto-deleted, normal operations resume
# Claude can now Edit, Write, Bash, etc.
```

### Single Project Workflow

```bash
# 1. Set up required reads for a specific feature
.claude/hooks/require-reads.sh ./docs/feature-spec.md ./docs/api-design.md

# 2. Start a Claude session and ask to implement the feature
# Claude will try to Edit/Write but get blocked (Layer 2)

# 3. Claude receives the blocking message and knows to read the files first
# Claude: "I need to read these files first..."
# [Reads ./docs/feature-spec.md]
# [Reads ./docs/api-design.md]

# 4. All files read - tracking file auto-deleted, normal operations resume
# Claude can now Edit, Write, Bash, etc.
```

## Integration with Skills

You can integrate this into skills by having them set up required reads:

```bash
# In a skill's entry script
.claude/hooks/require-reads.sh \
  "$CLAUDE_PROJECT_DIR/ARCHITECTURE.md" \
  "$CLAUDE_PROJECT_DIR/PROJECT_STRUCTURE.md"

# Then provide context to Claude about what it should do
echo "Please review the architecture and structure docs first."
```

## Testing the Hook

Test the hook script manually:

```bash
# Simulate a Bash tool call (should be blocked if tracking file exists)
echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | \
  .claude/hooks/block-until-reads.sh
echo "Exit code: $?"  # Should be 2 (blocked) if files not read

# Simulate a Read tool call for a required file (should be allowed)
echo '{"tool_name":"Read","tool_input":{"file_path":"/path/to/required/file.md"}}' | \
  .claude/hooks/block-until-reads.sh
echo "Exit code: $?"  # Should be 0 (allowed)
```

## Hook Configuration

The hook is configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/block-until-reads.sh"
          }
        ]
      }
    ]
  }
}
```

This applies to **all tool calls** (no matcher specified).

## Tracking File Format

`/tmp/claude-required-reads.json`:

```json
{
  "files": {
    "/absolute/path/to/file1.md": false,
    "/absolute/path/to/file2.py": true,
    "/absolute/path/to/file3.md": false
  }
}
```

- `false`: File not yet read
- `true`: File has been read

## Advanced: Custom Messages

You can modify `block-until-reads.sh` to customize the blocking message or add additional logic:

```bash
# Example: Add project-specific context
ERROR_MSG+="
📚 Why these files?
  - ARCHITECTURE.md: Understand the system design
  - PROJECT_STRUCTURE.md: Know where everything lives
  - CLAUDE.md: Learn development conventions

This ensures you have proper context before making changes."
```

## Troubleshooting

**Hook not firing?**
- Check `.claude/settings.json` has the PreToolUse configuration
- Ensure script is executable: `chmod +x .claude/hooks/block-until-reads.sh`
- Verify `$CLAUDE_PROJECT_DIR` is set correctly

**Files not being marked as read?**
- Check that the file paths in the tracking file are **absolute paths**
- The `require-reads.sh` script auto-converts relative to absolute paths

**Want to bypass temporarily?**
- Run: `.claude/hooks/require-reads.sh --clear`
- Or manually: `rm /tmp/claude-required-reads.json`

## Learn More

- [Claude Code Hooks Documentation](https://code.claude.com/docs/en/hooks)
- [PreToolUse Hook Reference](https://code.claude.com/docs/en/hooks#pretooluse)
- [Hooks Guide](https://code.claude.com/docs/en/hooks-guide)
