#!/usr/bin/env python3
"""Check every URL and relative link in the repo's Markdown files (stdlib only).

Classes:
  OK         2xx after redirects
  BLOCKED    401/403/429/999 or a bot wall; needs a manual or browser check
  SOFT_404   200 but the page title/body says "not found"
  NOT_FOUND  404/410
  ERROR      timeout, DNS, TLS, 5xx
Relative links are checked against the filesystem.

Exit status: 1 if any NOT_FOUND, SOFT_404, ERROR or broken relative link.
Usage: python tools/check_links.py [--repo PATH] [--json out.json] [--workers 12]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

URL_RE = re.compile(r"https?://[^\s<>\"'`)\]]+")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
TOOL_UA = "curl/8.9.1"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
SOFT404 = re.compile(r"<title>[^<]*(not found|404|page does not exist)[^<]*</title>", re.I)
SKIP_DIRS = {".git", ".work", "node_modules", "__pycache__"}


def md_files(repo: Path):
    for p in sorted(repo.rglob("*.md")):
        if not SKIP_DIRS.intersection(p.relative_to(repo).parts):
            yield p


def clean(url: str) -> str:
    url = url.rstrip(".,;:!?*_")
    while url.endswith(")") and url.count("(") < url.count(")"):
        url = url[:-1]
    return url


def check(url: str, timeout: float) -> tuple[str, int | None, str]:
    # Some hosts (developers.meta.com) 400 a browser UA that lacks sec-ch-* headers,
    # others 403 non-browser UAs; try an honest tool UA first, then a browser UA.
    first = None
    for ua in (TOOL_UA, UA):
        result = _fetch(url, timeout, ua)
        if result[0] == "OK" or result[1] not in (400, 403):
            return result
        first = first or result
    return first


def _fetch(url: str, timeout: float, ua: str) -> tuple[str, int | None, str]:
    target = url.split("#", 1)[0]
    ctx = ssl.create_default_context()
    req = urllib.request.Request(target, headers={"User-Agent": ua, "Accept": "text/html,*/*;q=0.8",
                                                  "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(262144).decode("utf-8", "replace")
            if SOFT404.search(body):
                return "SOFT_404", r.status, r.geturl()
            return "OK", r.status, r.geturl()
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return "NOT_FOUND", e.code, ""
        if e.code in (400, 401, 403, 429, 999):
            return "BLOCKED", e.code, ""
        if e.code == 405:
            return "OK", e.code, "method not allowed but host answered"
        return "ERROR", e.code, str(e.reason)
    except Exception as e:  # noqa: BLE001 - report every failure class
        return "ERROR", None, f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--json", help="write the full report here")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--timeout", type=float, default=25.0)
    args = ap.parse_args()
    repo = Path(args.repo)

    where: dict[str, set[str]] = {}
    broken_rel: list[str] = []
    for md in md_files(repo):
        text = md.read_text(encoding="utf-8")
        rel = md.relative_to(repo).as_posix()
        for u in URL_RE.findall(text):
            where.setdefault(clean(u), set()).add(rel)
        for target in LINK_RE.findall(text):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
                continue
            path = target.split("#", 1)[0]
            if path and not (md.parent / path).resolve().exists():
                broken_rel.append(f"{rel}: {target}")

    results = {}
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(check, u, args.timeout): u for u in where}
        for f in cf.as_completed(futs):
            results[futs[f]] = f.result()

    counts: dict[str, int] = {}
    for status, _, _ in results.values():
        counts[status] = counts.get(status, 0) + 1
    bad = {u: r for u, r in results.items() if r[0] in ("NOT_FOUND", "SOFT_404", "ERROR")}
    blocked = {u: r for u, r in results.items() if r[0] == "BLOCKED"}

    print(f"URLs: {len(results)}  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    for u, (s, code, info) in sorted(bad.items()):
        print(f"{s:9} {code or '-':>4} {u}  <- {', '.join(sorted(where[u]))}  {info}")
    for u, (s, code, _) in sorted(blocked.items()):
        print(f"BLOCKED   {code or '-':>4} {u}")
    for b in broken_rel:
        print(f"BROKEN-REL {b}")
    if args.json:
        Path(args.json).write_text(json.dumps({
            "counts": counts,
            "results": {u: {"status": s, "code": c, "info": i, "files": sorted(where[u])}
                        for u, (s, c, i) in sorted(results.items())},
            "broken_relative": broken_rel,
        }, indent=2), encoding="utf-8")
    return 1 if bad or broken_rel else 0


if __name__ == "__main__":
    sys.exit(main())
