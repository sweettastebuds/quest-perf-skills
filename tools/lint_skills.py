#!/usr/bin/env python3
"""Lint every SKILL.md in the marketplace (stdlib only).

Checks, per skill:
  * frontmatter starts on line 1 and parses (simple YAML subset: scalars,
    quoted scalars, folded/literal block scalars)
  * name: present, 1-64 chars, lowercase a-z0-9 and single hyphens, no
    leading/trailing hyphen, equals the folder name, unique across bundles
  * description: present, 1-1024 chars, no XML-like tags
  * body length (warn > 400 lines, error > 500 lines)
  * the seven required body sections are present
  * every relative link resolves; every references/* and scripts/* file is
    mentioned from SKILL.md (so the agent knows when to read/run it)
  * every `plugin:skill` cross-reference names an existing skill
Across skills:
  * duplicate quoted trigger phrases in descriptions (warning)
  * description token overlap (Jaccard) above a threshold (warning)

Exit status: 0 if no errors (warnings allowed), 1 otherwise.
Usage: python tools/lint_skills.py [--repo PATH] [--overlap 0.30] [--json]
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from pathlib import Path

PLUGINS = ("quest-perf", "unity-perf", "gles3-perf", "arm-mobile-hw-perf")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
XREF_RE = re.compile(r"\b(" + "|".join(map(re.escape, PLUGINS)) + r"):([a-z0-9]+(?:-[a-z0-9]+)*)\b")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
QUOTED_RE = re.compile(r"[\"“]([^\"”]{3,60})[\"”]")
REQUIRED_SECTIONS = {
    "when to use": re.compile(r"when to use", re.I),
    "diagnose first": re.compile(r"diagnos", re.I),
    "key numbers": re.compile(r"key numbers|numbers", re.I),
    "fixes": re.compile(r"fixes", re.I),
    "verify": re.compile(r"verif", re.I),
    "pitfalls and myths": re.compile(r"pitfall|myth", re.I),
    "sources": re.compile(r"sources", re.I),
}
STOP = set(
    """a an and are as at be by for from in into is it its of on or that the this to use
    when with load skill skills covers cover unity quest meta urp vs via per not only
    your you what which how also any all can do does e g eg i ie user types says
    """.split()
)


def parse_frontmatter(text: str):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, "frontmatter must start on line 1 with ---"
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None, text, "frontmatter has no closing ---"
    fm: dict[str, str] = {}
    i = 1
    while i < end:
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            return None, text, f"frontmatter line {i + 1} is not 'key: value': {line!r}"
        key, val = m.group(1), m.group(2).rstrip()
        if val in (">", "|", ">-", "|-", ">+", "|+"):
            block = []
            i += 1
            while i < end and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            joiner = " " if val.startswith(">") else "\n"
            fm[key] = joiner.join(b for b in block if b).strip()
            continue
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            inner = val[1:-1]
            if val[0] == "'":
                val = inner.replace("''", "'")
            else:
                val = re.sub(r'\\(["\\/])', r"\1", inner).replace("\\n", "\n").replace("\\t", "\t")
        elif val.startswith(("\"", "'")):
            return None, text, f"unterminated quoted scalar for {key!r}"
        elif ": " in val or val.startswith(("[", "{", "&", "*", "!", "%", "@", "`")):
            return None, text, f"plain scalar for {key!r} contains YAML-significant characters; quote it"
        fm[key] = val
        i += 1
    body = "\n".join(lines[end + 1 :])
    return fm, body, None


def tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9][a-z0-9+./-]*", s.lower()) if t not in STOP and len(t) > 2}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--overlap", type=float, default=0.30, help="Jaccard warning threshold")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    repo = Path(args.repo)

    errors: list[str] = []
    warnings: list[str] = []
    skills: dict[str, dict] = {}
    by_plugin: dict[str, set[str]] = {p: set() for p in PLUGINS}

    for plugin in PLUGINS:
        sdir = repo / "plugins" / plugin / "skills"
        if not sdir.is_dir():
            warnings.append(f"{plugin}: no skills/ directory")
            continue
        for skill_md in sorted(sdir.glob("*/SKILL.md")):
            folder = skill_md.parent.name
            rel = skill_md.relative_to(repo).as_posix()
            text = skill_md.read_text(encoding="utf-8")
            fm, body, err = parse_frontmatter(text)
            if err:
                errors.append(f"{rel}: {err}")
                continue
            name = fm.get("name", "")
            desc = fm.get("description", "")
            if not name:
                errors.append(f"{rel}: missing name")
            else:
                if len(name) > 64:
                    errors.append(f"{rel}: name longer than 64 chars ({len(name)})")
                if not NAME_RE.match(name):
                    errors.append(f"{rel}: name {name!r} is not lowercase kebab-case without consecutive/edge hyphens")
                if name != folder:
                    errors.append(f"{rel}: name {name!r} does not match folder {folder!r}")
                if name in skills:
                    errors.append(f"{rel}: name {name!r} duplicates {skills[name]['path']}")
            if not desc:
                errors.append(f"{rel}: missing description")
            else:
                if len(desc) > 1024:
                    errors.append(f"{rel}: description is {len(desc)} chars (> 1024)")
                if re.search(r"<[A-Za-z/][^>]*>", desc):
                    errors.append(f"{rel}: description contains an XML-like tag")
            extra = set(fm) - {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
            if extra:
                warnings.append(f"{rel}: frontmatter keys outside the Agent Skills spec: {sorted(extra)}")

            body_lines = body.count("\n") + 1
            if body_lines > 500:
                errors.append(f"{rel}: body is {body_lines} lines (> 500)")
            elif body_lines > 400:
                warnings.append(f"{rel}: body is {body_lines} lines (> ~400 target)")

            headings = [m.group(1) for m in (HEADING_RE.match(l) for l in body.splitlines()) if m]
            for label, rx in REQUIRED_SECTIONS.items():
                if not any(rx.search(h) for h in headings):
                    errors.append(f"{rel}: missing required section '{label}'")

            skill_dir = skill_md.parent
            for md in [skill_md, *sorted((skill_dir / "references").glob("*.md"))]:
                mtext = md.read_text(encoding="utf-8")
                for target in LINK_RE.findall(mtext):
                    if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                        continue
                    path = target.split("#", 1)[0]
                    if path and not (md.parent / path).resolve().exists():
                        errors.append(f"{md.relative_to(repo).as_posix()}: broken relative link {target!r}")
            for sub in ("references", "scripts"):
                d = skill_dir / sub
                if d.is_dir():
                    for f in sorted(p for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
                        relf = f.relative_to(skill_dir).as_posix()
                        if relf not in body and f.name not in body:
                            warnings.append(f"{rel}: {relf} is never mentioned in SKILL.md")

            skills[name or folder] = {"path": rel, "plugin": plugin, "desc": desc, "body": body, "dir": skill_dir}
            by_plugin[plugin].add(name or folder)

    # cross-bundle references
    for name, s in skills.items():
        texts = [s["body"]] + [p.read_text(encoding="utf-8") for p in sorted((s["dir"] / "references").glob("*.md"))]
        for t in texts:
            for plugin, target in XREF_RE.findall(t):
                if target not in by_plugin.get(plugin, set()):
                    errors.append(f"{s['path']}: cross-reference {plugin}:{target} does not exist")

    # trigger-overlap heuristics
    quoted: dict[str, list[str]] = {}
    for name, s in skills.items():
        for q in QUOTED_RE.findall(s["desc"]):
            quoted.setdefault(q.lower().strip(), []).append(name)
    for q, names in sorted(quoted.items()):
        if len(set(names)) > 1:
            warnings.append(f"trigger phrase \"{q}\" appears in several descriptions: {sorted(set(names))}")
    overlaps = []
    for (a, sa), (b, sb) in itertools.combinations(skills.items(), 2):
        ta, tb = tokens(sa["desc"]), tokens(sb["desc"])
        if ta and tb:
            j = len(ta & tb) / len(ta | tb)
            if j >= args.overlap:
                overlaps.append((j, a, b))
    for j, a, b in sorted(overlaps, reverse=True):
        warnings.append(f"description overlap {j:.2f}: {a} <-> {b}")

    report = {
        "skills": len(skills),
        "per_plugin": {p: sorted(v) for p, v in by_plugin.items()},
        "description_lengths": {n: len(s["desc"]) for n, s in skills.items()},
        "errors": errors,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Skills: {len(skills)}  " + "  ".join(f"{p}={len(v)}" for p, v in by_plugin.items()))
        for e in errors:
            print(f"ERROR   {e}")
        for w in warnings:
            print(f"WARN    {w}")
        print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
