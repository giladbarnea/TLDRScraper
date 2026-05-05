#!/usr/bin/env -S uv run
# /// script
# requires-python = "==3.12.*"
# dependencies = ["rich"]
# ///
"""
Output PR review comments as Markdown, with diff_hunk code context.

Usage: uv run scripts/dev/pr-review-comments.py [PR_NUMBER] [-r]

If PR_NUMBER is omitted, auto-detects from the current branch.
-r / --rich: render and page output via Rich.
"""
import argparse
import json
import subprocess
import sys


def run(command: str) -> str:
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Command failed: {command}\n{result.stderr}")
    return result.stdout.strip()


def detect_pr_number() -> int:
    output = run("gh pr view --json number --jq .number")
    return int(output)


def fetch_inline_comments(pr_number: int) -> list[dict]:
    raw = run(f"gh api repos/:owner/:repo/pulls/{pr_number}/comments")
    return json.loads(raw)


def fetch_review_summary(pr_number: int) -> list[dict]:
    raw = run(f"gh api repos/:owner/:repo/pulls/{pr_number}/reviews")
    reviews = json.loads(raw)
    return [r for r in reviews if r.get("body", "").strip()]


def format_diff_hunk(hunk: str, lang: str) -> str:
    return f"```diff\n{hunk}\n```"


def guess_lang(path: str) -> str:
    ext = path.rsplit(".", 1)[-1] if "." in path else ""
    return {
        "js": "js", "jsx": "jsx", "ts": "ts", "tsx": "tsx",
        "py": "python", "sh": "bash", "json": "json", "md": "markdown",
    }.get(ext, "")


def render_inline_comment(comment: dict, index: int) -> str:
    path: str = comment["path"]
    line: int = comment.get("line") or comment.get("original_line", "?")
    body: str = comment["body"].strip()
    hunk: str = comment.get("diff_hunk", "").strip()
    author: str = comment["user"]["login"]
    url: str = comment["html_url"]
    lang = guess_lang(path)

    lines = [
        f"## Comment {index}: `{path}:{line}`",
        f"**Author:** [{author}]({url})  ",
        "",
        format_diff_hunk(hunk, lang),
        "",
        body,
    ]
    return "\n".join(lines)


def render_review_summary(review: dict) -> str:
    body: str = review["body"].strip()
    author: str = review["user"]["login"]
    state: str = review["state"]
    url: str = review["html_url"]
    return "\n".join([
        f"## Review Summary",
        f"**Author:** [{author}]({url}) · **State:** {state}",
        "",
        body,
    ])


def output(content: str, rich_mode: bool) -> None:
    if not rich_mode:
        print(content)
        return
    from rich.console import Console
    from rich.markdown import Markdown
    console = Console()
    with console.pager(styles=True):
        console.print(Markdown(content))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pr_number", nargs="?", type=int, help="PR number (auto-detected if omitted)")
    parser.add_argument("-r", "--rich", action="store_true", help="Render and page output via Rich")
    args = parser.parse_args()

    pr_number = args.pr_number or detect_pr_number()
    rich_mode = args.rich

    sections: list[str] = [f"# PR #{pr_number} — Review Comments"]

    reviews = fetch_review_summary(pr_number)
    for review in reviews:
        sections.append(render_review_summary(review))

    comments = fetch_inline_comments(pr_number)
    if not comments:
        sections.append("_No inline review comments._")
    else:
        for index, comment in enumerate(comments, start=1):
            sections.append(render_inline_comment(comment, index))

    output("\n\n---\n\n".join(sections), rich_mode)


main()
