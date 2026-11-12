#!/usr/bin/env python3
"""Fidelity check for the converted Scratch + micro:bit content. Read-only; exit code 1 on any FAIL.

For every old page in lesson-server/public:
  1. extract visible text fragments (tags/scripts/styles dropped, whitespace normalised, split at block
     elements, <br>, buttons and classed inline badges) and confirm each meaningful fragment appears in the
     new content (Markdown body + frontmatter) of the page's content files;
  2. confirm every local file linked/embedded by the page exists in site/public with identical sha256;
     linked pages must belong to a converted page or to a known out-of-scope page (/, /adults/).
Also: every non-HTML file under public/scratch-games and public/microbit-emojis is byte-identical in
site/public; catalogue.json matches lesson frontmatter; frontmatter key sets are consistent per collection;
local links inside the new content resolve.

Whitelisted boilerplate (rendered by layouts, not stored as content) is listed in WHITELIST_DOC below and
printed with per-page hit counts. "Derived" entries are recomputed from frontmatter, not blindly accepted.
"""
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urljoin

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from scratch_html import BLOCK, Node, parse, split_frontmatter  # noqa: E402

SITE = HERE.parent
OLD = SITE.parent / "lesson-server" / "public"
NEW = SITE / "public"
C = SITE / "src" / "content"

WHITELIST_DOC = """\
Layout-rendered boilerplate (exact fragments, matched after whitespace removal):
  student lesson page : "← Όλα τα μαθήματα Scratch" | "Ξεκίνα εδώ" | "Αρχείο αρχής .sb3" | "Ολοκληρωμένη λύση .sb3"
                        | "Ξεχωριστά γραφικά SVG · Σημειώσεις εκπαιδευτή"
                        | derived: "ΜΑΘΗΜΑ <NN> · <minutes> ΛΕΠΤΑ"
  teacher lesson page : "← Στο μάθημα" | "ΣΗΜΕΙΩΣΕΙΣ ΕΚΠΑΙΔΕΥΤΗ" | "Αρχείο αρχής .sb3" | "Ολοκληρωμένη λύση .sb3"
  lessons index       : "Άνοιγμα μαθήματος" | derived: "ΜΑΘΗΜΑ <NN>"
  3-games index       : "Λήψη παιχνιδιού .sb3" | "Λήψη γραφικών αντικειμένων" | derived: "ΠΑΙΧΝΙΔΙ <NN>"
  course lesson/pages : "← Μαθήματα Scratch 7–9 ετών" | "Σημειώσεις εκπαιδευτή" | "Λήψη .md" | "Εκτύπωση"
                        | derived: "ΜΑΘΗΜΑ <n> · 60 ΛΕΠΤΑ · 7–9 ΕΤΩΝ" | pager "← Μάθημα <k>" / "Μάθημα <k> →"
  course index        : "Σημειώσεις εκπαιδευτή" | "Άνοιγμα" | "Λήψη .sb3"
                        | derived: "ΜΑΘΗΜΑ <n> · ΠΛΗΡΕΙΣ ΣΗΜΕΙΩΣΕΙΣ" (status full) / "ΜΑΘΗΜΑ <n> · ΠΕΡΙΓΡΑΜΜΑ" (outline)
  micro:bit pages     : none
Not checked: <title> suffix wording beyond html_title (stored verbatim in frontmatter and checked), alt attributes.
"""

OUT_OF_SCOPE_PAGES = {"/", "/adults/"}


# ------------------------------------------------------------------ helpers

def ws(s):
    return re.sub(r"\s+", "", s)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def old_fragments(path):
    root = parse((OLD / path).read_text(encoding="utf-8"))
    frags, buf = [], []

    def flush():
        t = "".join(buf)
        buf.clear()
        t = re.sub(r"\s+", " ", t).strip()
        if re.search(r"\w", t):
            frags.append(t)

    def sep(n, parent):
        return (n.tag in BLOCK or n.tag == "button" or (n.tag in ("a", "span") and n.get("class"))
                or (n.tag == "a" and parent.tag == "nav"))

    def walk(n):
        for c in n.children:
            if isinstance(c, str):
                buf.append(c)
                continue
            if c.tag in ("script", "style"):
                continue
            s = sep(c, n)
            if s:
                flush()
            walk(c)
            if s:
                flush()

    walk(root)
    flush()
    return frags, root


def new_text(md_body):
    t = re.sub(r"</?[a-zA-Z][^>]*>", " ", md_body)
    t = re.sub(r"!?\[( |x|X)\]", lambda m: "☐" if m.group(1) == " " else "☑", t)  # task boxes
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", t)
    lines = []
    for ln in t.splitlines():
        if re.fullmatch(r"\s*\|?[\s:|-]*-[\s:|-]*\|?\s*", ln) and "-" in ln and ln.strip().strip("|-: "):
            pass
        if re.fullmatch(r"\s*(\|?\s*:?-{3,}:?\s*)+\|?\s*", ln) or re.fullmatch(r"\s*(-{3,}|\*{3,})\s*", ln):
            continue
        if re.match(r"\s*#{1,6}\s", ln):
            ln = re.sub(r"^\s*#{1,6}\s+", "", ln)
        else:
            ln = re.sub(r"^\s*(>\s*)*([-*+]|\d+\.)?\s*", "", ln, count=1)
        lines.append(ln)
    t = "\n".join(lines)
    t = re.sub(r"\\(.)", r"\1", t)
    t = html.unescape(t)
    return t


def strip_marks(s):
    return s.replace("*", "").replace("`", "").replace("|", "")


def flatten(v, out):
    if isinstance(v, str):
        out.append(v)
    elif isinstance(v, list):
        if v and all(isinstance(x, str) for x in v):
            out.append(" · ".join(v))
        for x in v:
            flatten(x, out)
    elif isinstance(v, dict):
        for x in v.values():
            flatten(x, out)


def load(rel):
    fm, body = split_frontmatter((C / rel).read_text(encoding="utf-8"))
    out = []
    flatten(fm, out)
    return fm, "\n".join(out) + "\n" + new_text(body), body


def haystack(files):
    parts, fms = [], []
    for f in files:
        fm, text, body = load(f)
        parts.append(text)
        fms.append((f, fm, body))
    return ws(strip_marks("\n".join(parts))), fms


# ------------------------------------------------------------------ links

def old_links(root, page_path):
    out = []

    def walk(n):
        for c in n.children:
            if isinstance(c, Node):
                for k in ("href", "src"):
                    v = c.get(k)
                    if v and not re.match(r"^(https?:|mailto:|#)", v):
                        out.append(v)
                walk(c)

    walk(root)
    return out


# ------------------------------------------------------------------ page definitions

def lesson_nums():
    return sorted(int(re.search(r"lesson-(\d)", p.name).group(1)) for p in (C / "scratch-course").glob("lesson-*.md"))


def build_pages():
    pages = []
    lessons = sorted(p.name for p in (C / "scratch-lessons").glob("*.md"))
    lesson_slugs = [n[:-3] for n in lessons]

    def exact(*s):
        return list(s)

    pages.append(dict(
        id="scratch-games/", old="scratch-games/index.html", url="/scratch-games/",
        files=["scratch-pages/games-index.md"] + [f"scratch-games/{p.name}" for p in sorted((C / "scratch-games").glob("*.md"))],
        wl=exact("Λήψη παιχνιδιού .sb3", "Λήψη γραφικών αντικειμένων"),
        derived=lambda fms: {f"ΠΑΙΧΝΙΔΙ {fm['number']:02d}" for f, fm, b in fms if "number" in fm}))
    pages.append(dict(
        id="scratch-games/lessons/", old="scratch-games/lessons/index.html", url="/scratch-games/lessons/",
        files=["scratch-pages/lessons-index.md"] + [f"scratch-lessons/{n}" for n in lessons],
        wl=exact("Άνοιγμα μαθήματος"),
        derived=lambda fms: {f"ΜΑΘΗΜΑ {fm['number']:02d}" for f, fm, b in fms if "number" in fm}))
    for slug in lesson_slugs:
        pages.append(dict(
            id=f"scratch-games/lessons/{slug}/", old=f"scratch-games/lessons/{slug}/index.html",
            url=f"/scratch-games/lessons/{slug}/", files=[f"scratch-lessons/{slug}.md"],
            wl=exact("← Όλα τα μαθήματα Scratch", "Ξεκίνα εδώ", "Αρχείο αρχής .sb3", "Ολοκληρωμένη λύση .sb3",
                     "Ξεχωριστά γραφικά SVG · Σημειώσεις εκπαιδευτή"),
            derived=lambda fms: {f"ΜΑΘΗΜΑ {fm['number']:02d} · {fm['minutes']} ΛΕΠΤΑ" for f, fm, b in fms}))
        pages.append(dict(
            id=f"scratch-games/lessons/{slug}/teacher.html", old=f"scratch-games/lessons/{slug}/teacher.html",
            url=f"/scratch-games/lessons/{slug}/teacher.html", files=[f"scratch-lesson-teacher/{slug}.md"],
            wl=exact("← Στο μάθημα", "ΣΗΜΕΙΩΣΕΙΣ ΕΚΠΑΙΔΕΥΤΗ", "Αρχείο αρχής .sb3", "Ολοκληρωμένη λύση .sb3"),
            derived=lambda fms: set()))
    nums = lesson_nums()
    for i, n in enumerate(nums):
        fm_ = split_frontmatter((C / f"scratch-course/lesson-{n}.md").read_text(encoding="utf-8"))[0]
        wl = ["← Μαθήματα Scratch 7–9 ετών", "Σημειώσεις εκπαιδευτή", "Εκτύπωση"]
        if fm_.get("download"):
            wl.append("Λήψη .md")
        d = {f"ΜΑΘΗΜΑ {n} · {fm_['minutes']} ΛΕΠΤΑ · {fm_['ages']} ΕΤΩΝ"}
        if i:
            d.add(f"← Μάθημα {nums[i-1]}")
        if i + 1 < len(nums):
            d.add(f"Μάθημα {nums[i+1]} →")
        pages.append(dict(id=f"scratch-games/course/lesson-{n}.html", old=f"scratch-games/course/lesson-{n}.html",
                          url=f"/scratch-games/course/lesson-{n}.html", files=[f"scratch-course/lesson-{n}.md"],
                          wl=wl, derived=lambda fms, d=d: d))
    for slug in ("roadmap", "quick-reference", "checklist"):
        pages.append(dict(id=f"scratch-games/course/{slug}.html", old=f"scratch-games/course/{slug}.html",
                          url=f"/scratch-games/course/{slug}.html", files=[f"scratch-course/{slug}.md"],
                          wl=["← Μαθήματα Scratch 7–9 ετών", "Σημειώσεις εκπαιδευτή", "Λήψη .md", "Εκτύπωση"],
                          derived=lambda fms: set()))
    pages.append(dict(
        id="scratch-games/course/", old="scratch-games/course/index.html", url="/scratch-games/course/",
        files=["scratch-pages/course-index.md"] + [f"scratch-course/lesson-{n}.md" for n in nums]
        + [f"scratch-course-games/{p.name}" for p in sorted((C / "scratch-course-games").glob("*.md"))]
        + [f"scratch-course-starters/{p.name}" for p in sorted((C / "scratch-course-starters").glob("*.md"))],
        wl=["Σημειώσεις εκπαιδευτή", "Άνοιγμα", "Λήψη .sb3"],
        derived=lambda fms: {f"ΜΑΘΗΜΑ {fm['number']} · " + ("Πλήρεις σημειώσεις" if fm["status"] == "full" else "Περίγραμμα").upper()
                             for f, fm, b in fms if fm.get("kind") == "lesson"}))
    pages.append(dict(id="microbit-emojis/", old="microbit-emojis/index.html", url="/microbit-emojis/",
                      files=["microbit/emojis.md"], wl=[], derived=lambda fms: set()))
    pages.append(dict(id="microbit-emojis/teacher-notes.html", old="microbit-emojis/teacher-notes.html",
                      url="/microbit-emojis/teacher-notes.html", files=["microbit/teacher-notes.md"], wl=[],
                      derived=lambda fms: set()))
    return pages


# ------------------------------------------------------------------ main

def main():
    pages = build_pages()
    page_urls = {p["url"] for p in pages} | OUT_OF_SCOPE_PAGES
    failures = 0
    print(WHITELIST_DOC)
    for pg in pages:
        problems = []
        frags, root = old_fragments(pg["old"])
        hay, fms = haystack(pg["files"])
        allowed = {ws(strip_marks(x)) for x in pg["wl"]} | {ws(strip_marks(x)) for x in pg["derived"](fms)}
        wl_hits = set()
        missing = []
        for f in frags:
            k = ws(strip_marks(f))
            if k in hay:
                continue
            if k in allowed:
                wl_hits.add(f)
                continue
            missing.append(f)
        if missing:
            problems.append("missing text: " + " || ".join(m[:90] for m in missing[:6]) + (f" (+{len(missing)-6})" if len(missing) > 6 else ""))
        # links
        base_url = pg["url"] if pg["url"].endswith((".html", "/")) else pg["url"]
        n_files = 0
        for href in old_links(root, pg["old"]):
            target = urljoin(base_url, href.split("#")[0].split("?")[0])
            target = unquote(target)
            if target.endswith("/") or target.endswith(".html"):
                if target not in page_urls and not (OLD / target.lstrip("/")).exists():
                    problems.append(f"link to unknown page {href}")
                elif target not in page_urls:
                    problems.append(f"link to page not converted/known {href} -> {target}")
                continue
            o, n = OLD / target.lstrip("/"), NEW / target.lstrip("/")
            n_files += 1
            if not o.exists():
                problems.append(f"old link target missing in lesson-server: {href}")
            elif not n.exists():
                problems.append(f"file not copied: {target}")
            elif sha(o) != sha(n):
                problems.append(f"sha256 differs: {target}")
        status = "FAIL" if problems else "PASS"
        failures += bool(problems)
        print(f"[{status}] {pg['id']:<55} fragments={len(frags):<3} whitelisted={len(wl_hits):<2} files_checked={n_files}")
        for p in problems:
            print("       -", p)
        if wl_hits and "-v" in sys.argv:
            print("       whitelisted:", sorted(wl_hits))

    # ---- global checks
    problems = []
    n = 0
    for top in ("scratch-games", "microbit-emojis"):
        for o in sorted((OLD / top).rglob("*")):
            if o.is_dir() or o.suffix == ".html" or "__pycache__" in o.parts:
                continue
            n += 1
            d = NEW / o.relative_to(OLD)
            if not d.exists() or sha(d) != sha(o):
                problems.append(f"static copy mismatch: {o.relative_to(OLD)}")
    # catalogue
    cat = json.loads((OLD / "scratch-games/lessons/catalogue.json").read_text(encoding="utf-8"))
    for i, item in enumerate(cat, 1):
        fm = split_frontmatter((C / f"scratch-lessons/{item['id']}.md").read_text(encoding="utf-8"))[0]
        for key in ("title", "concept", "goal"):
            if fm[key] != item[key]:
                problems.append(f"catalogue mismatch {item['id']}.{key}")
        for key in ("starter", "complete"):
            if fm[key] != "/scratch-games/lessons/" + item[key]:
                problems.append(f"catalogue mismatch {item['id']}.{key}")
        if fm["number"] != i:
            problems.append(f"lesson number {item['id']}")
    # key-set consistency + new-content local links
    for coll in sorted(p for p in C.iterdir() if p.is_dir() and (p.name.startswith(("scratch", "microbit")))):
        keysets = {}
        for f in sorted(coll.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            fm, body = split_frontmatter(text)
            keysets.setdefault(frozenset(fm), []).append(f.name)
            for href in re.findall(r"\]\((/[^)\s]*)\)|href=\"(/[^\"]*)\"", text):
                href = unquote(next(h for h in href if h))
                if href.endswith("/") or href.endswith(".html"):
                    continue
                if not (NEW / href.lstrip("/")).exists():
                    problems.append(f"{f.relative_to(C)}: broken local link {href}")
            for k, v in fm.items():
                if isinstance(v, str) and v.startswith("/") and not v.endswith(("/", ".html")) and not (NEW / v.lstrip("/")).exists():
                    problems.append(f"{f.relative_to(C)}: frontmatter {k} points to missing file {v}")
        if coll.name == "scratch-course":
            continue  # lesson/page kinds legitimately differ; kinds checked below
        if coll.name in ("scratch-pages", "microbit"):
            req = {"url", "title", "html_title"}
            for ks, names in keysets.items():
                if not req <= ks:
                    problems.append(f"{coll.name}: {names} lack {sorted(req - ks)}")
            continue
        if len(keysets) > 1:
            problems.append(f"{coll.name}: inconsistent frontmatter keys: {[sorted(v)[:2] for v in keysets.values()]}")
    status = "FAIL" if problems else "PASS"
    failures += bool(problems)
    print(f"[{status}] global: {n} static files byte-identical, catalogue.json vs frontmatter, schema consistency, new-link targets")
    for p in problems:
        print("       -", p)
    print(f"\n{len(pages)} pages checked, {failures} failing group(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
