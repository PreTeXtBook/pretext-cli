#!/usr/bin/env python3
"""
pr_desc.py â€” Draft a PR description from a git diff.

Safe by default:
- Local git diff only. No network calls unless you pass --llm and set env vars.

Usage:
  python3 scripts/pr_desc.py --base main --head HEAD > PR_DESCRIPTION.md
  python3 scripts/pr_desc.py --staged > PR_DESCRIPTION.md
  python3 scripts/pr_desc.py --base v1.2.0 --head HEAD --llm > PR_DESCRIPTION.md
"""
import argparse
import os
import subprocess
import json
import urllib.request


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr}")
    return p.stdout


def git_diff(base: str | None, head: str | None, staged: bool) -> str:
    if staged:
        return run(["git", "diff", "--staged"])
    if base and head:
        return run(["git", "diff", f"{base}...{head}"])
    return run(["git", "diff", "HEAD~1..HEAD"])  # default: last commit


def heuristic_summary(diff_text: str) -> str:
    lines = diff_text.splitlines()
    added = sum(1 for ln in lines if ln.startswith("+") and not ln.startswith("+++"))
    removed = sum(1 for ln in lines if ln.startswith("-") and not ln.startswith("---"))
    files = [ln[6:] for ln in lines if ln.startswith("+++ b/")]
    subsystems = sorted({(f.split("/")[0] if "/" in f else "(root)") for f in files})
    title = (
        f"Draft: Update {files[0]} (+{added}/-{removed}, {len(files)} files)"
        if files
        else "Draft: Update codebase"
    )

    bullets = []
    if added or removed:
        bullets.append(
            f"Code changes: **+{added} / -{removed}** across **{len(files)} file(s)**."
        )
    if subsystems:
        bullets.append("Touches: " + ", ".join(subsystems))
    if any("test" in f.lower() for f in files):
        bullets.append("Includes test changes.")
    if any(f.endswith((".md", ".txt")) for f in files):
        bullets.append("Includes documentation updates.")

    body = (
        "\n".join(f"- {b}" for b in bullets) if bullets else "- Minor internal changes."
    )
    return f"""# {title}

## What changed
{body}

## Why
Briefly explain the problem/goal addressed in this PR.

## How to verify
- [ ] Run unit tests
- [ ] Manual verification steps

## Risks & rollbacks
- Risk level: Low / Medium / High
- Rollback: `git revert <merge-commit>` or feature flag off
"""


def llm_summary(diff_text: str) -> str | None:
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    if not api_key:
        return None
    prompt = f"""
You are helping write a crisp GitHub Pull Request description.
Summarize the unified diff that follows. Output Markdown only with these sections:

# <Concise PR title, 8â€“12 words>

## What changed
- 4â€“8 bullets with concrete changes

## Why
- 1â€“3 bullets giving rationale and user impact

## How to verify
- checklist of commands or steps

## Risks & rollbacks
- risk level
- how to revert safely

Unified diff:
{diff_text[:200000]}
"""
    data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert release engineer. Be precise and concise.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"]
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base")
    ap.add_argument("--head")
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--llm", action="store_true")
    args = ap.parse_args()

    diff_text = git_diff(args.base, args.head, args.staged)
    if args.llm:
        md = llm_summary(diff_text)
        if md:
            print(md)
            return
    print(heuristic_summary(diff_text))


if __name__ == "__main__":
    main()
