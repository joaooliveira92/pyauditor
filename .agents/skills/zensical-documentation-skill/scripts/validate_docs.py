#!/usr/bin/env python3
import argparse, re, sys
from pathlib import Path
from urllib.parse import unquote

LINK_RE=re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
H_RE=re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
SECRET_RE=re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}")

def slug(s):
    s=re.sub(r"[`*_~]", "", s).strip().lower()
    s=re.sub(r"[^\w\- ]", "", s, flags=re.UNICODE)
    return re.sub(r"[\s-]+", "-", s).strip("-")

def main():
    ap=argparse.ArgumentParser(description="Validate a Markdown documentation tree")
    ap.add_argument("project", nargs="?", default=".")
    args=ap.parse_args(); root=Path(args.project).resolve(); docs=root/"docs"
    errors=[]; warnings=[]
    if not ((root/"zensical.toml").exists() or (root/"mkdocs.yml").exists()): errors.append("Missing zensical.toml or mkdocs.yml")
    if not docs.exists(): errors.append("Missing docs directory")
    if not (docs/"index.md").exists() and not (docs/"README.md").exists(): errors.append("Missing documentation home page")
    if docs.exists():
      for d in [docs, *[p for p in docs.rglob("*") if p.is_dir()]]:
        if (d/"README.md").exists() and (d/"index.md").exists(): errors.append(f"Both README.md and index.md exist: {d.relative_to(root)}")
      for f in docs.rglob("*.md"):
        text=f.read_text(encoding="utf-8")
        hs=H_RE.findall(text); h1=sum(1 for marks,_ in hs if len(marks)==1)
        if h1==0: warnings.append(f"No H1: {f.relative_to(root)}")
        if h1>1: errors.append(f"Multiple H1 headings: {f.relative_to(root)}")
        if SECRET_RE.search(text): errors.append(f"Possible secret: {f.relative_to(root)}")
        anchors={slug(title) for _,title in hs}
        for raw in LINK_RE.findall(text):
          raw=raw.strip().split(maxsplit=1)[0].strip("<>")
          if not raw or raw.startswith(("http://","https://","mailto:","tel:","data:")): continue
          path_part, _, frag=unquote(raw).partition("#")
          target=(f.parent/path_part).resolve() if path_part else f
          try: target.relative_to(root)
          except ValueError: errors.append(f"Link escapes project in {f.relative_to(root)}: {raw}"); continue
          if path_part and not target.exists(): errors.append(f"Broken link in {f.relative_to(root)}: {raw}")
          elif frag and target.suffix.lower()==".md" and target.exists():
            th={slug(t) for _,t in H_RE.findall(target.read_text(encoding="utf-8"))}
            if frag not in th: warnings.append(f"Unresolved fragment in {f.relative_to(root)}: {raw}")
    for x in errors: print("ERROR:", x)
    for x in warnings: print("WARN:", x)
    print(f"Validation complete: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0
if __name__ == "__main__": sys.exit(main())
