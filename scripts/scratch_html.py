"""Tiny HTML tree + HTML->Markdown helpers shared by convert_scratch.py and check_scratch.py.

Standard library only. Read-only with respect to everything it parses.
"""
import html
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

VOID = {"input", "br", "img", "meta", "link", "hr"}
BLOCK = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "div", "section", "article",
         "details", "summary", "main", "header", "footer", "nav", "ul", "ol", "table", "tr",
         "thead", "tbody", "pre", "label", "blockquote", "body", "html", "head", "title", "br"}


class Node:
    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = attrs or []
        self.children = []

    def get(self, name, default=None):
        for k, v in self.attrs:
            if k == name:
                return v
        return default

    def classes(self):
        return (self.get("class") or "").split()

    def text(self):
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs)
        self.stack[-1].children.append(n)
        if tag not in VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse(src):
    b = _Builder()
    b.feed(src)
    b.close()
    return b.root


def find(node, tag, cls=None):
    for c in node.children:
        if isinstance(c, Node):
            if c.tag == tag and (cls is None or cls in c.classes()):
                return c
            r = find(c, tag, cls)
            if r:
                return r
    return None


def find_all(node, tag):
    out = []
    for c in node.children:
        if isinstance(c, Node):
            if c.tag == tag:
                out.append(c)
            out.extend(find_all(c, tag))
    return out


def elements(node):
    """Element children, ignoring whitespace-only text."""
    return [c for c in node.children if isinstance(c, Node)]


def serialize(n):
    if isinstance(n, str):
        return html.escape(n, quote=False)
    attrs = "".join(f' {k}' if v is None else f' {k}="{html.escape(v, quote=True)}"' for k, v in n.attrs)
    if n.tag in VOID:
        return f"<{n.tag}{attrs}>"
    return f"<{n.tag}{attrs}>" + "".join(serialize(c) for c in n.children) + f"</{n.tag}>"


def plain(n):
    return re.sub(r"\s+", " ", n.text()).strip()


# ---------------------------------------------------------------- HTML -> Markdown

def fix_href(href, page_url):
    """Make local links absolute (site-root) so Markdown is location independent."""
    if re.match(r"^(https?:|mailto:|#)", href):
        return href
    return urljoin(page_url, href)


def _quote(href):
    return href.replace(" ", "%20").replace(")", "%29").replace("(", "%28")


def esc(t):
    t = t.replace("\\", "\\\\").replace("&", "&amp;")
    for ch in "*_`[]":
        t = t.replace(ch, "\\" + ch)
    return t.replace("<", "&lt;")


def raw(n):
    s = serialize(n)
    return re.sub(r"\n[ \t]*\n+", "\n", s)


def inline(children, page_url):
    out = []
    for c in children:
        if isinstance(c, str):
            out.append(esc(re.sub(r"\s+", " ", c)))
            continue
        t = c.tag
        if t in ("strong", "b", "em", "i"):
            inner = inline(c.children, page_url)
            core = inner.strip()
            if core:
                mark = "**" if t in ("strong", "b") else "*"
                lead = " " if inner[:1] == " " else ""
                trail = " " if inner[-1:] == " " else ""
                out.append(f"{lead}{mark}{core}{mark}{trail}")
        elif t == "code":
            s = c.text()
            out.append(f"`{s}`" if "`" not in s else raw(c))
        elif t == "a" and c.get("href") is not None and plain(c):
            inner = inline(c.children, page_url).strip()
            out.append(f"[{inner}]({_quote(fix_href(c.get('href'), page_url))})")
        elif t == "br":
            out.append("<br>")
        else:
            out.append(raw(c))
    return "".join(out)


def _para(children, page_url):
    s = re.sub(r"\s+", " ", inline(children, page_url)).strip()
    if re.match(r"(\d+[.)]|[-+>#])(\s|$)", s):
        s = "\\" + s
    return s


def _list(n, page_url):
    items = []
    for li in elements(n):
        if li.tag != "li" or any(isinstance(c, Node) and c.tag in BLOCK for c in li.children):
            return raw(n)
        items.append(_para(li.children, page_url))
    if n.tag == "ul":
        return "\n".join(f"- {i}" for i in items)
    return "\n".join(f"{k}. {i}" for k, i in enumerate(items, 1))


def _table(n, page_url):
    rows = []
    for tr in find_all(n, "tr"):
        rows.append([_para(c.children, page_url).replace("|", "\\|") for c in elements(tr)])
    head, body = rows[0], rows[1:]
    lines = ["| " + " | ".join(head) + " |", "| " + " | ".join("---" for _ in head) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def blocks(nodes, page_url, keep_sections=False):
    """Convert a list of sibling nodes into Markdown block strings. Unknown/classed
    elements are passed through as raw HTML (no blank lines inside, so Markdown keeps them as one block)."""
    out = []
    for n in nodes:
        if isinstance(n, str):
            if n.strip():
                out.append(_para([n], page_url))
            continue
        t = n.tag
        plain_el = not n.attrs
        if re.fullmatch(r"h[1-6]", t) and plain_el:
            out.append("#" * int(t[1]) + " " + _para(n.children, page_url))
        elif t == "p" and plain_el:
            s = _para(n.children, page_url)
            if s:
                out.append(s)
        elif t in ("ul", "ol") and plain_el:
            out.append(_list(n, page_url))
        elif t == "table" and plain_el:
            out.append(_table(n, page_url))
        elif t == "div" and n.classes() == ["table-wrap"]:
            out.extend(blocks(elements(n), page_url, keep_sections))
        elif t == "details" and plain_el:
            summ = find(n, "summary")
            rest = [c for c in n.children if c is not summ]
            out.append("<details>\n<summary>" + html.escape(plain(summ), quote=False) + "</summary>")
            out.extend(blocks(rest, page_url, keep_sections))
            out.append("</details>")
        elif t == "section" and plain_el and keep_sections:
            out.append("<section>")
            out.extend(blocks(n.children, page_url, keep_sections))
            out.append("</section>")
        else:
            out.append(raw(n))
    return out


def to_markdown(nodes, page_url, keep_sections=False):
    return "\n\n".join(blocks(nodes, page_url, keep_sections)) + "\n"


# ---------------------------------------------------------------- frontmatter

import json


def frontmatter(d):
    """Every value is JSON (a valid YAML flow scalar/sequence/mapping), one key per line."""
    lines = ["---"]
    for k, v in d.items():
        if v is None:
            continue
        lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def split_frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n?(.*)\Z", text, re.S)
    fm = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(": ")
        fm[k] = json.loads(v)
    return fm, m.group(2)
