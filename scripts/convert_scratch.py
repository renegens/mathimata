#!/usr/bin/env python3
"""Convert the Scratch + micro:bit sections of the lesson server into Markdown content files.

Reads (read-only):
  ../../lesson-server/public/...           current generated website
  ../../lesson-server/tools/prepare_scratch_course.py   (Greek titles/goals/descriptions, imported without running)
  ../../scratch-course-7-9/                original course Markdown
Writes (only creates/overwrites files this script owns; never deletes):
  ../src/content/{scratch-pages,scratch-games,scratch-lessons,scratch-lesson-teacher,
                  scratch-course,scratch-course-games,scratch-course-starters,microbit}/*.md
  ../public/scratch-games/**, ../public/microbit-emojis/**   (byte-identical copies of every non-HTML file)
"""
import importlib.util
import re
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from scratch_html import (Node, blocks, elements, find, find_all, frontmatter, fix_href, inline,  # noqa: E402
                          parse, plain, to_markdown)

SITE = HERE.parent
LS = SITE.parent / "lesson-server"
PUB = LS / "public"
COURSE_SRC = SITE.parent / "scratch-course-7-9"
CONTENT = SITE / "src" / "content"
OUT_PUB = SITE / "public"

spec = importlib.util.spec_from_file_location("prepare_scratch_course", LS / "tools" / "prepare_scratch_course.py")
psc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(psc)


def write(rel, text):
    p = CONTENT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def page_doc(path):
    return parse((PUB / path).read_text(encoding="utf-8"))


def html_title(root):
    t = find(root, "title")
    return plain(t) if t else None


def main_of(root):
    m = find(root, "main")
    return [c for c in m.children if not (isinstance(c, str) and not c.strip())]


def cls(n, c):
    assert isinstance(n, Node) and c in n.classes(), (n.tag, n.attrs, c)
    return n


def link(a, url):
    return {"label": plain(a), "href": fix_href(a.get("href"), url)}


def wrap_inline_runs(children):
    """Wrap loose inline nodes (bare <a>/text directly inside a section) into a synthetic <p>."""
    out, run = [], []
    for c in children:
        if isinstance(c, Node) and c.tag not in ("a", "strong", "em", "code", "span"):
            if run:
                p = Node("p")
                p.children = run
                out.append(p)
                run = []
            out.append(c)
        else:
            run.append(c)
    if any(not isinstance(r, str) or r.strip() for r in run):
        p = Node("p")
        p.children = run
        out.append(p)
    return out


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ------------------------------------------------------------------ copy static files

def copy_static():
    n = 0
    for top in ("scratch-games", "microbit-emojis"):
        for src in sorted((PUB / top).rglob("*")):
            if src.is_dir() or src.suffix == ".html" or "__pycache__" in src.parts:
                continue
            dst = OUT_PUB / src.relative_to(PUB)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            n += 1
    return n


# ------------------------------------------------------------------ (a) 3 games page

def convert_games():
    url = "/scratch-games/"
    root = page_doc("scratch-games/index.html")
    k = main_of(root)
    back, label, h1, promo1, promo2, lede, dl, grid, help_ = k
    promos = []
    for s in (promo1, promo2):
        h2, p, a = elements(s)
        promos.append({"heading": plain(h2), "text": plain(p), **{"cta_" + x: v for x, v in link(a, url).items()}})
    games = []
    for i, art in enumerate(elements(grid), 1):
        img, tag, h2, p, a1, a2 = [c for c in art.children if isinstance(c, Node)]
        sb3 = a1.get("href")
        slug = slugify(Path(sb3).stem)
        games.append((i, slug, {
            "number": i, "slug": slug, "title": plain(h2), "description": plain(p),
            "icon": fix_href(img.get("src"), url), "sb3": fix_href(sb3, url),
            "assets_zip": fix_href(a2.get("href"), url)}))
    for i, slug, d in games:
        write(f"scratch-games/{slug}.md", frontmatter(d))
    # help section: h2 + ol + p + p(links)
    body = to_markdown(wrap_inline_runs(help_.children), url)
    fm = {"id": "games-index", "url": url, "html_title": html_title(root), "back": link(back, url),
          "tag": plain(cls(label, "label")), "title": plain(h1), "promos": promos, "lede": plain(lede),
          "download_all": link(dl, url)}
    write("scratch-pages/games-index.md", frontmatter(fm) + "\n" + body)
    return len(games)


# ------------------------------------------------------------------ (b) 8 lessons

def convert_lessons():
    base = "/scratch-games/lessons/"
    root = page_doc("scratch-games/lessons/index.html")
    back, tag, h1, intro, zipbtn, notes, grid, outro = main_of(root)
    fm = {"id": "lessons-index", "url": base, "html_title": html_title(root), "back": link(back, base),
          "tag": plain(tag), "title": plain(h1), "intro": plain(intro),
          "download_all": link(zipbtn, base), "teacher_notes": link(notes, base)}
    write("scratch-pages/lessons-index.md", frontmatter(fm) + "\n" + to_markdown([outro], base))

    import json
    catalogue = json.loads((PUB / "scratch-games/lessons/catalogue.json").read_text(encoding="utf-8"))
    for n, item in enumerate(catalogue, 1):
        slug = item["id"]
        sdir = f"scratch-games/lessons/{slug}/"
        surl = "/" + sdir
        # ---- student page
        root = page_doc(sdir + "index.html")
        k = main_of(root)
        back, tag, h1, muted, goal, panel, *rest = k
        cls(tag, "tag")
        cls(muted, "muted")
        cls(panel, "panel")
        minutes = int(re.search(r"(\d+) ΛΕΠΤΑ", plain(tag)).group(1))
        pk = elements(panel)
        _h2, start_p, a_start, a_done, links_p = pk
        zip_a, teach_a = find_all(links_p, "a")
        footnote, ref_p = rest[-1], rest[-2]
        cls(footnote, "muted")
        ref_a = find(ref_p, "a")
        assert plain(ref_p) == plain(ref_a)
        assert plain(muted) == item["concept"] and plain(goal) == item["goal"] and plain(h1) == item["title"]
        fm = {
            "number": n, "slug": slug, "title": plain(h1), "concept": plain(muted), "goal": plain(goal),
            "minutes": minutes, "start": plain(start_p),
            "starter": fix_href(a_start.get("href"), surl + "index.html"),
            "complete": fix_href(a_done.get("href"), surl + "index.html"),
            "assets_zip": fix_href(zip_a.get("href"), surl + "index.html"),
            "preview": surl + "preview.svg",
            "reference": {"label": plain(ref_a), "url": ref_a.get("href")},
            "footnote": plain(footnote),
            "html_title": html_title(root),
            "teacher_page": f"/scratch-games/lessons/{slug}/teacher.html",
        }
        body = to_markdown(rest[:-2], surl + "index.html")
        write(f"scratch-lessons/{slug}.md", frontmatter(fm) + "\n" + body)

        # ---- teacher page
        root = page_doc(sdir + "teacher.html")
        k = main_of(root)
        tback, ttag, th1, *trest = k
        trest = [x for x in trest if not (isinstance(x, Node) and x.tag == "a" and "button" in x.classes())]
        tfm = {"lesson": slug, "number": n, "title": plain(th1), "html_title": html_title(root),
               "student_page": surl}
        write(f"scratch-lesson-teacher/{slug}.md",
              frontmatter(tfm) + "\n" + to_markdown(trest, surl + "teacher.html"))
    return len(catalogue)


# ------------------------------------------------------------------ (c) course 7-9

def roadmap_outline(num):
    text = (COURSE_SRC / "Scratch - 8-Lesson Roadmap.md").read_text(encoding="utf-8")
    m = re.search(rf"^## Μ{num} .*?$(.*?)(?=^---|^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def convert_course():
    base = "/scratch-games/course/"
    for num, fname, title, goal in psc.LESSONS:
        if fname:
            md = (COURSE_SRC / fname).read_text(encoding="utf-8")
            md = re.sub(r"\A#[^\n]*\n", "", md).strip("\n") + "\n"
        else:
            md = "*Περίγραμμα — συμπληρώνεται μετά την πρώτη διδασκαλία.*\n\n" + roadmap_outline(num) + "\n"
        fm = {"kind": "lesson", "number": num, "slug": f"lesson-{num}", "title": title, "goal": goal,
              "status": "full" if fname else "outline", "minutes": 60, "ages": "7–9",
              "download": f"{base}files/lesson-{num}.md" if fname else None,
              "html_title": f"Μάθημα {num}: {title} · Scratch"}
        write(f"scratch-course/lesson-{num}.md", frontmatter(fm) + "\n" + md)
    for slug, fname, title in psc.EXTRA:
        md = re.sub(r"\A#[^\n]*\n", "", (COURSE_SRC / fname).read_text(encoding="utf-8")).strip("\n") + "\n"
        fm = {"kind": "page", "slug": slug, "title": title, "download": f"{base}files/{slug}.md",
              "html_title": f"{title} · Scratch"}
        write(f"scratch-course/{slug}.md", frontmatter(fm) + "\n" + md)

    for i, (f, t, d, keys) in enumerate(psc.GAMES, 1):
        fm = {"order": i, "slug": f, "title": t, "description": d,
              "concepts": [c.strip() for c in keys.split("·")],
              "file": f"{base}games/{f}.sb3", "screenshot": f"{base}games/{f}.png",
              "author": "Jesse Smith", "license": "BSD-3-Clause", "license_file": f"{base}games/LICENSE.txt"}
        write(f"scratch-course-games/{f}.md", frontmatter(fm))
    for i, (f, t, d) in enumerate(psc.STARTERS, 1):
        fn = f.replace(" ", "-")
        fm = {"order": i, "slug": slugify(f), "title": t, "description": d,
              "file": f"{base}starters/{fn}.sb3", "author": "Scratch Team (scratch.mit.edu)"}
        write(f"scratch-course-starters/{slugify(f)}.md", frontmatter(fm))

    # index page
    root = page_doc("scratch-games/course/index.html")
    k = main_of(root)
    back, tag, h1, muted, zipbtn, *rest = k
    buttons, rest = [], rest
    while isinstance(rest[0], Node) and rest[0].tag == "a":
        buttons.append(rest.pop(0))
    sections, panel = [], rest.pop()
    cls(panel, "panel")
    assert len(rest) == 9
    for sid, (h2, intro, grid) in zip(("lessons", "starters", "games"), (rest[0:3], rest[3:6], rest[6:9])):
        sections.append({"id": sid, "heading": plain(_h2_without_badge(h2)),
                         "intro": plain(intro)})
    fm = {"id": "course-index", "url": base, "html_title": html_title(root),
          "back": link(back, base), "tag": plain(tag), "title": plain(h1), "intro": plain(muted),
          "download_all": link(zipbtn, base), "pages": [link(b, base) for b in buttons],
          "sections": sections}
    for c in elements(panel):  # drop presentational attrs (style, class=muted) so the panel is plain Markdown
        c.attrs = []
    write("scratch-pages/course-index.md", frontmatter(fm) + "\n" + to_markdown(panel.children, base))


def _h2_without_badge(h2):
    n = Node("h2")
    n.children = [c for c in h2.children if not (isinstance(c, Node) and c.tag == "span")]
    return n


# ------------------------------------------------------------------ (d) micro:bit

def convert_microbit():
    base = "/microbit-emojis/"
    # student page
    url = base
    root = page_doc("microbit-emojis/index.html")
    main = find(root, "main")
    nav, header, *secs, footer = elements(main)
    assert nav.tag == "nav" and header.tag == "header" and footer.tag == "footer"
    tag, h1, lead, intro = elements(header)
    foot_p, foot_back = elements(footer)
    fm = {"slug": "emojis", "url": base, "html_title": html_title(root), "title": plain(h1),
          "tag": plain(tag), "lead": plain(lead), "intro": plain(intro),
          "nav": [link(a, url) for a in find_all(nav, "a")],
          "footer_back": link(foot_back, url),
          "scripts": [fix_href(s.get("src"), url) for s in find_all(root, "script")],
          "stylesheets": [fix_href(s.get("href"), url) for s in find_all(root, "link")],
          "downloads": [{"label": "JavaScript", "href": base + "emojis.js"}],
          "teacher_page": base + "teacher-notes.html",
          "designer": "Raw HTML block in the body: <div class=\"designer\"> (needs scripts[] loaded, "
                      "see CONTENT.md)"}
    body = to_markdown(secs + [foot_p], url, keep_sections=True)
    write("microbit/emojis.md", frontmatter(fm) + "\n" + body)

    # teacher notes
    turl = base + "teacher-notes.html"
    root = page_doc("microbit-emojis/teacher-notes.html")
    main = find(root, "main")
    nav, header, *secs = elements(main)
    tag, h1, intro = elements(header)
    tfm = {"slug": "teacher-notes", "url": turl, "html_title": html_title(root), "title": plain(h1),
           "tag": plain(tag), "intro": plain(intro),
           "nav": [link(a, turl) for a in find_all(nav, "a")],
           "stylesheets": [fix_href(s.get("href"), turl) for s in find_all(root, "link")]}
    write("microbit/teacher-notes.md", frontmatter(tfm) + "\n" + to_markdown(secs, turl, keep_sections=True))


def main():
    n = copy_static()
    print(f"copied {n} static files into {OUT_PUB}")
    print("games:", convert_games())
    print("lessons:", convert_lessons())
    convert_course()
    convert_microbit()
    print("content written under", CONTENT)


if __name__ == "__main__":
    main()
