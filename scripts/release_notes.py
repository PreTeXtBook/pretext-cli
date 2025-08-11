#!/usr/bin/env python3
"""
release_notes.py â€” Generate release notes from merged commits/PR titles.

Safe by default:
- Works locally using git history. No network calls.
- Optional LLM polish via any OpenAI-compatible endpoint *only* if you pass --llm and set env vars.

Usage:
  python3 scripts/release_notes.py --last-tag > RELEASE_NOTES.md
  python3 scripts/release_notes.py --since v1.2.0 --until HEAD > RELEASE_NOTES.md
  python3 scripts/release_notes.py --since v1.2.0 --llm > RELEASE_NOTES.md

Optional env (OpenAI-compatible chat API) if you use --llm:
  LLM_API_KEY       = your key
  LLM_BASE_URL      = https://api.openai.com/v1   (or your own endpoint)
  LLM_MODEL         = gpt-4o-mini                 (or any served model)
"""
import argparse, os, subprocess, re, json, urllib.request

def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr}")
    return p.stdout

def last_tag() -> str | None:
    try:
        return run(["git", "describe", "--tags", "--abbrev=0"]).strip()
    except Exception:
        return None

def commits(since: str | None = None, until: str = "HEAD") -> list[str]:
    rng = f"{since}..{until}" if since else until
    # Prefer merge subjects first (often carry PR titles)
    log = run(["git", "log", "--merges", "--pretty=%s", rng])
    if not log.strip():
        log = run(["git", "log", "--pretty=%s", rng])
    return [ln.strip() for ln in log.splitlines() if ln.strip()]

def categorize(msgs: list[str]) -> dict[str, list[str]]:
    cats = {k: [] for k in ["feat","fix","perf","docs","refactor","test","build","ci","chore","other"]}
    pat = re.compile(r"^(feat|fix|perf|docs|refactor|test|build|ci|chore)(\(.+?\))?:\s*(.+)$", re.I)
    for m in msgs:
        mt = pat.match(m)
        if mt:
            cats[mt.group(1).lower()].append(mt.group(3))
        else:
            cats["other"].append(m)
    return cats

def format_notes(cats: dict[str, list[str]], since: str | None, until: str) -> str:
    title = f"Release Notes ({since} â†’ {until})" if since else f"Release Notes (up to {until})"
    order = ["feat","fix","perf","refactor","docs","test","build","ci","chore","other"]
    labels = {
        "feat":"Features","fix":"Fixes","perf":"Performance","refactor":"Refactoring",
        "docs":"Documentation","test":"Tests","build":"Build","ci":"CI","chore":"Chore","other":"Other"
    }
    out = [f"# {title}", ""]
    for k in order:
        items = cats.get(k, [])
        if items:
            out.append(f"## {labels[k]}")
            out.extend(f"- {it}" for it in items)
            out.append("")
    out.append("â€” Generated locally by release_notes.py")
    return "\n".join(out)

def llm_polish(markdown: str) -> str | None:
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    if not api_key:
        return None
    prompt = f"""Rewrite the following release notes for clarity and concision.
Keep headings and lists in Markdown. Do not invent changes.

{markdown[:200000]}
"""
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a meticulous technical editor."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(data).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"]
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="tag/ref to start from (e.g., v1.2.0)")
    ap.add_argument("--until", default="HEAD", help="end ref (default HEAD)")
    ap.add_argument("--last-tag", action="store_true", help="use last tag as --since")
    ap.add_argument("--llm", action="store_true", help="polish output via LLM if env vars set")
    args = ap.parse_args()

    since = args.since or (last_tag() if args.last_tag else None)
    msgs = commits(since, args.until)
    cats = categorize(msgs)
    md = format_notes(cats, since, args.until)
    if args.llm:
        polished = llm_polish(md)
        if polished:
            print(polished)
            return
    print(md)

if __name__ == "__main__":
    main()

