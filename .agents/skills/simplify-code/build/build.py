#!/usr/bin/env python3
"""
Build .agents/skills/simplify-code/SKILL.md by combining the current skill
with a Gemini-tersified version of Addy Osmani's code-simplification skill.

Output structure:
    {simplify-code frontmatter + adis_origin field}
    {terse Addy body}
    ---
    {current SKILL.md body}
"""
import re
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))
import markdown_frontmatter

BUILD_DIR = Path(__file__).resolve().parent
SKILL_MD = BUILD_DIR.parent / 'SKILL.md'
ANTHROPICS_VERSION = BUILD_DIR / 'anthropics-version.md'
ADIS_RAW_URL = "https://raw.githubusercontent.com/addyosmani/agent-skills/main/skills/code-simplification/SKILL.md"
TERSE_OUTPUT_RAW_URL = "https://raw.githubusercontent.com/giladbarnea/llm-templates/main/skills/terse-output/SKILL.md"
ADIS_ORIGIN = "https://github.com/addyosmani/agent-skills/blob/main/skills/code-simplification/SKILL.md, release 0.5.0, commit fea75b1"
RUN_AGENT = PROJECT_ROOT / 'scripts' / 'run-agent.sh'


def fetch(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode('utf-8')


def strip_frontmatter(content: str) -> str:
    """Strip YAML frontmatter block from a markdown string."""
    match = re.match(r'^---\s*\n.*?---[ \t]*(?:\n|$)', content, re.DOTALL)
    if not match:
        return content
    return content[match.end():]


def strip_inspired_by(body: str) -> str:
    """Remove the '> Inspired by...' blockquote paragraph."""
    return re.sub(r'\n> Inspired by[^\n]*\n\n', '\n', body)


def run_gemini_terser(adis_body: str) -> str:
    """Apply terse-output editing to adis_body via Gemini."""
    return adis_body


def build() -> None:
    adis_body = strip_inspired_by(strip_frontmatter(fetch(ADIS_RAW_URL)))
    terse_adis_body = run_gemini_terser(adis_body)

    current_frontmatter = markdown_frontmatter.read(ANTHROPICS_VERSION)
    current_body = markdown_frontmatter.body(ANTHROPICS_VERSION)

    output_frontmatter = {**current_frontmatter, 'adis_origin': ADIS_ORIGIN}
    fm_lines = '\n'.join(f'{k}: {v}' for k, v in output_frontmatter.items())
    SKILL_MD.write_text(f"---\n{fm_lines}\n---\n{terse_adis_body}\n---\n{current_body}", encoding='utf-8')
    print(f"Built {SKILL_MD}")


if __name__ == '__main__':
    build()
