#!/usr/bin/env python3
"""Check a built site folder.

usage: check_site.py DIST [--base /mathimata/] [--old ../lesson-server/public] [-v]

 (a) every HTML page of the old site exists in DIST at the same path
 (b) every internal href/src/url() in DIST (HTML + CSS) resolves to a file under the given base
     (root-relative URLs outside the base are errors; #fragments are checked for local pages)
 (c) every .sb3/.zip/.pdf/.md file in DIST that also exists in the old site is byte-identical,
     and every such old file exists in DIST
 (d) for every old HTML page the visible text, fragment by fragment (block level), appears in the new page

Exit code 1 if anything fails.  Whitelist for (d) is explicit and short (see WHITELIST below).
"""
import argparse, hashlib, html, re, sys, unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit, urljoin

SITE = Path(__file__).resolve().parents[1]
DEFAULT_OLD = SITE.parent / 'lesson-server' / 'public'

# ---- (d) whitelist: old fragments that are intentionally not reproduced verbatim -------------------
# key: regex on the old page path (relative to old root); value: set of normalised old fragments.
WHITELIST = {
    r'^adult-lesson-01-internet/index\.html$': {
        # old placeholder written by an inline script; new lessons.js writes "Ολοκληρώθηκαν N από 6" at runtime
        'Ολοκληρώθηκαν 0 από 6',
    },
}
# Glyphs dropped everywhere: old course pages showed ☐/☑ as text, the new pages use real checkboxes.
IGNORED_GLYPHS = '☐☑'

BLOCK = {'p', 'div', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'td', 'th', 'tr', 'table', 'section',
         'article', 'nav', 'header', 'footer', 'main', 'aside', 'button', 'label', 'details', 'summary', 'pre',
         'blockquote', 'br', 'hr', 'caption', 'form', 'textarea', 'select', 'option', 'figure', 'figcaption', 'body'}
SKIP = {'script', 'style', 'head', 'title', 'template', 'noscript'}
VOID = {'br', 'hr', 'img', 'input', 'meta', 'link', 'source', 'area', 'base', 'col', 'embed', 'wbr'}


def norm(s):
    for g in IGNORED_GLYPHS:
        s = s.replace(g, '')
    s = re.sub(r'\s+', ' ', html.unescape(s)).strip()
    if s and s == s.upper() and re.search('[Α-Ωα-ω]', s):
        # ALL-CAPS labels: the old pages had stray tonos inside capitals (e.g. "ΠΛΉΡΕΙΣ"); compare without accents
        s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


class Visible(HTMLParser):
    """Collects block-level text fragments."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.cur = []
        self.frags = []
        self.hidden_stack = []

    def flush(self):
        t = norm(''.join(self.cur))
        if t:
            self.frags.append(t)
        self.cur = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            if tag not in VOID:
                self.skip += 1
            return
        if tag in BLOCK:
            self.flush()
        if tag == 'img':
            pass

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if tag in BLOCK:
            self.flush()

    def handle_data(self, data):
        if not self.skip:
            self.cur.append(data)

    def close(self):
        super().close()
        self.flush()


def visible_fragments(text):
    p = Visible()
    p.feed(text)
    p.close()
    return p.frags


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []   # (attr, value)
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            self.ids.add(a['id'])
        if tag == 'a' and a.get('name'):
            self.ids.add(a['name'])
        for attr in ('href', 'src', 'poster', 'action', 'data-src'):
            if a.get(attr) is not None and tag != 'base':
                self.links.append((f'{tag}[{attr}]', a[attr]))
        if a.get('srcset'):
            for part in a['srcset'].split(','):
                if part.strip():
                    self.links.append((f'{tag}[srcset]', part.strip().split()[0]))
        if a.get('style'):
            for m in re.finditer(r'url\(([^)]+)\)', a['style']):
                self.links.append((f'{tag}[style]', m.group(1).strip('\'" ')))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dist')
    ap.add_argument('--base', default='/')
    ap.add_argument('--old', default=str(DEFAULT_OLD))
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()
    dist, old = Path(args.dist).resolve(), Path(args.old).resolve()
    base = '/' + args.base.strip('/') + '/' if args.base.strip('/') else '/'
    errors = []

    def err(group, msg):
        errors.append((group, msg))

    if not dist.is_dir():
        sys.exit(f'dist folder not found: {dist}')
    old_pages = sorted(p.relative_to(old).as_posix() for p in old.rglob('*.html'))
    new_pages = sorted(p.relative_to(dist).as_posix() for p in dist.rglob('*.html'))

    # ---- (a) ----
    missing = [p for p in old_pages if not (dist / p).is_file()]
    for p in missing:
        err('a', f'old page missing from build: {p}')
    for extra in ('index.html', 'adults/index.html'):   # these were server-generated listings in the old site
        if not (dist / extra).is_file():
            err('a', f'expected page missing: {extra}')
    print(f'(a) old pages: {len(old_pages)} checked, {len(missing)} missing  [{len(new_pages)} html pages in build]')

    # ---- (b) ----
    page_ids = {}
    n_links = 0
    bad_b = 0

    def url_to_file(path):
        """site path (already base-stripped, starts with '/') -> existing Path or None / 'DIR'."""
        path = unquote(path)
        cand = dist / path.lstrip('/')
        if path.endswith('/') or path == '':
            f = cand / 'index.html'
            return f if f.is_file() else ('DIR' if cand.is_dir() else None)
        if cand.is_file():
            return cand
        if cand.is_dir():
            return 'DIR'
        return None

    def check_url(src_desc, page_url, value):
        nonlocal n_links, bad_b
        v = html.unescape(value).strip()
        if not v or v.startswith(('#',)) and len(v) == 1:
            return
        if re.match(r'^(mailto:|tel:|javascript:|data:|blob:)', v, re.I):
            return
        if re.match(r'^(https?:)?//', v, re.I):
            return   # external
        n_links += 1
        parts = urlsplit(v)
        if v.startswith('#'):
            target_url = page_url
        else:
            target_url = urljoin(page_url, parts.path)
            if parts.path == '':
                target_url = page_url
        if not target_url.startswith(base) and target_url != base.rstrip('/'):
            bad_b += 1
            err('b', f'{src_desc}: {value!r} resolves to {target_url} which is outside base {base}')
            return
        rel = '/' + target_url[len(base):].lstrip('/') if target_url != base.rstrip('/') else '/'
        f = url_to_file(rel)
        if f is None:
            bad_b += 1
            err('b', f'{src_desc}: {value!r} -> {rel} not found')
        elif f == 'DIR':
            bad_b += 1
            err('b', f'{src_desc}: {value!r} -> {rel} is a folder without index.html (would 404 on a static host)')
        elif parts.fragment and f.suffix == '.html':
            ids = page_ids.get(f)
            if ids is None:
                p = Links()
                p.feed(f.read_text(encoding='utf-8'))
                ids = page_ids[f] = p.ids
            if unquote(parts.fragment) not in ids and parts.fragment not in ids and parts.fragment != 'top':
                bad_b += 1
                err('b', f'{src_desc}: fragment #{parts.fragment} not found in {rel}')

    for page in new_pages:
        text = (dist / page).read_text(encoding='utf-8')
        pu = base + (page[:-len('index.html')] if page.endswith('index.html') else page)
        parser = Links()
        parser.feed(text)
        for what, v in parser.links:
            check_url(f'{page} {what}', pu, v)
    for css in dist.rglob('*.css'):
        rel = css.relative_to(dist).as_posix()
        cu = base + rel
        for m in re.finditer(r'url\(([^)]+)\)', css.read_text(encoding='utf-8')):
            check_url(f'{rel} url()', cu, m.group(1).strip('\'" '))
    print(f'(b) internal links/assets: {n_links} checked under base {base}, {bad_b} broken')

    # ---- (c) ----
    exts = {'.sb3', '.zip', '.pdf', '.md'}
    n_c = bad_c = 0
    for f in sorted(old.rglob('*')):
        if f.is_file() and f.suffix.lower() in exts:
            rel = f.relative_to(old)
            n_c += 1
            g = dist / rel
            if not g.is_file():
                bad_c += 1
                err('c', f'download missing in build: {rel}')
            elif sha(f) != sha(g):
                bad_c += 1
                err('c', f'download differs from old site: {rel}')
    for g in sorted(dist.rglob('*')):
        if g.is_file() and g.suffix.lower() in exts and not (old / g.relative_to(dist)).is_file():
            print(f'    note: {g.relative_to(dist)} has no counterpart in the old site (not compared)')
    print(f'(c) downloads (.sb3 .zip .pdf .md): {n_c} compared with old site, {bad_c} problems')

    # ---- (d) ----
    n_d = bad_d = 0
    for page in old_pages:
        new = dist / page
        if not new.is_file():
            continue
        n_d += 1
        old_frags = visible_fragments((old / page).read_text(encoding='utf-8'))
        new_text = ' ' + ' '.join(visible_fragments(new.read_text(encoding='utf-8'))) + ' '
        new_compact = re.sub(r'\s+', '', new_text)
        allow = set()
        for pat, items in WHITELIST.items():
            if re.search(pat, page):
                allow |= items
        miss = []
        for fr in old_frags:
            if fr in allow:
                continue
            if fr in new_text or re.sub(r'\s+', '', fr) in new_compact:
                continue
            miss.append(fr)
        if miss:
            bad_d += 1
            for fr in miss:
                err('d', f'{page}: old text not found in new page: {fr[:160]!r}')
        elif args.verbose:
            print(f'    ok  {page} ({len(old_frags)} fragments)')
    print(f'(d) visible text: {n_d} old pages compared, {bad_d} with missing text')

    if errors:
        print(f'\nFAILED: {len(errors)} problem(s)')
        shown = {}
        for g, m in errors:
            shown[g] = shown.get(g, 0) + 1
            if shown[g] <= 40:
                print(f'  [{g}] {m}')
        for g, c in shown.items():
            if c > 40:
                print(f'  [{g}] ... and {c - 40} more')
        sys.exit(1)
    print('\nOK: all site checks passed')


if __name__ == '__main__':
    main()
