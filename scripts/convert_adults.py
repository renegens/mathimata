#!/usr/bin/env python3
"""Convert the adult course (lesson-server/public) into Markdown content files.

Reads from lesson-server (read-only). Writes only under site/ :
  src/content/adults/NN-slug.md
  src/content/adults-guide/teacher-guide.md
  public/adult-materials/*  (copies of shared assets)
Never deletes anything; re-running overwrites only files this script generates.
"""
import json, re, shutil, sys
from html.parser import HTMLParser
from pathlib import Path

SRC = Path('/home/rgg/Work/teaching/lesson-server/public')
SITE = Path(__file__).resolve().parents[1]
OUT = SITE / 'src/content/adults'
OUT_GUIDE = SITE / 'src/content/adults-guide'

VOID = {'meta', 'link', 'input', 'br', 'img', 'hr'}

# exercise ids understood by adult-materials/lessons.js (None = plain link block)
EXERCISES = {2: 'note-app', 6: 'practice-form', 7: 'email-form', 8: 'typing', 9: 'copy-paste',
             11: 'quiz', 12: 'draft', 15: 'quiz', 16: 'calendar', 17: 'stock', 18: 'draft',
             19: 'draft', 20: None, 22: None, 24: None}

# ---------------------------------------------------------------- tiny DOM
class Node:
    def __init__(self, tag, attrs):
        self.tag, self.attrs, self.kids = tag, dict(attrs), []
    @property
    def cls(self): return (self.attrs.get('class') or '').split()
    def text(self):
        return ''.join(k if isinstance(k, str) else k.text() for k in self.kids)

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root', []); self.stack = [self.root]
    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs); self.stack[-1].kids.append(n)
        if tag not in VOID: self.stack.append(n)
    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]; return
    def handle_data(self, d): self.stack[-1].kids.append(d)

def parse(html):
    p = Parser(); p.feed(html); return p.root

def find(n, tag):
    for k in n.kids:
        if isinstance(k, Node):
            if k.tag == tag: return k
            r = find(k, tag)
            if r: return r

def ws(s): return re.sub(r'\s+', ' ', s).strip()

# ---------------------------------------------------------------- inline / block rendering
def inline(n):
    out = ''
    for k in n.kids:
        if isinstance(k, str): out += re.sub(r'\s+', ' ', k); continue
        if k.tag == 'strong': out += '**' + inline(k).strip() + '**'
        elif k.tag == 'kbd': out += '<kbd>' + inline(k) + '</kbd>'
        elif k.tag == 'a': out += '[' + inline(k).strip() + '](' + k.attrs['href'] + ')'
        elif k.tag == 'button':
            attrs = ''.join(f' {a}' + (f'="{v}"' if v is not None else '') for a, v in k.attrs.items())
            out += f'<button{attrs}>' + inline(k) + '</button>'
        else: out += inline(k)
    return out.strip()

def _btn(k):
    attrs = ''.join(f' {a}' + (f'="{v}"' if v is not None else '') for a, v in k.attrs.items())
    return f'<button{attrs}>' + inline(k) + '</button>'

def blocks(n, depth=0):
    """Render children of a container to Markdown blocks (list of strings)."""
    out = []
    for k in n.kids:
        if isinstance(k, str):
            if k.strip(): out.append(ws(k))
            continue
        t = k.tag
        if t in ('h2', 'h3'):
            out.append('#' * int(t[1]) + ' ' + inline(k))
        elif t == 'p':
            txt = inline(k)
            if 'help' in k.cls: out.append('> ' + txt)
            elif k.attrs.get('id') == 'progress': continue
            else: out.append(txt)
        elif t in ('ol', 'ul'):
            items = [inline(li) for li in k.kids if isinstance(li, Node) and li.tag == 'li']
            out.append('\n'.join((f'{i}. ' if t == 'ol' else '- ') + x for i, x in enumerate(items, 1)))
        elif t == 'label' and find(k, 'input') is not None:
            out.append('- [ ] ' + inline(k))
        elif t == 'div' and 'eyebrow' in k.cls:
            out.append(inline(k))
        elif t == 'div' and 'bar' in k.cls:
            items = [inline(a) for a in k.kids if isinstance(a, Node)]
            out.append('\n'.join('- ' + x for x in items))
        elif t == 'table':
            out.append(table(k))
        elif t == 'button':
            out.append(_btn(k))
        elif t in ('section', 'div'):
            out += blocks(k, depth + 1)
        else:
            raise ValueError('unhandled element ' + t)
    return out

def table(t):
    rows = []
    for tr in iter_tag(t, 'tr'):
        rows.append([inline(c) for c in tr.kids if isinstance(c, Node)])
    head = rows[0]
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] +
                     ['| ' + ' | '.join(r) + ' |' for r in rows[1:]])

def iter_tag(n, tag):
    for k in n.kids:
        if isinstance(k, Node):
            if k.tag == tag: yield k
            else: yield from iter_tag(k, tag)

# ---------------------------------------------------------------- frontmatter
def fm_value(v):
    if isinstance(v, bool): return 'true' if v else 'false'
    if v is None: return 'null'
    if isinstance(v, int): return str(v)
    if isinstance(v, list): return '[' + ', '.join(json.dumps(x, ensure_ascii=False) for x in v) + ']'
    return json.dumps(v, ensure_ascii=False)

def frontmatter(fields, teacher=None):
    s = '---\n' + ''.join(f'{k}: {fm_value(v)}\n' for k, v in fields)
    if teacher is not None:
        s += 'teacher: |\n' + ''.join(('  ' + l if l else '') + '\n' for l in teacher.split('\n'))
    return s + '---\n'

# ---------------------------------------------------------------- lesson conversion
def convert_lesson(folder):
    meta = json.loads((folder / 'lesson.json').read_text(encoding='utf-8'))
    html = (folder / 'index.html').read_text(encoding='utf-8')
    thtml = (folder / 'teacher-notes.html').read_text(encoding='utf-8')
    num = meta['number']
    main = find(parse(html), 'main')
    header = find(main, 'header')

    tagel = next(k for k in header.kids if isinstance(k, Node) and ('tag' in k.cls or 'eyebrow' in k.cls))
    ps = [k for k in header.kids if isinstance(k, Node) and k.tag == 'p' and 'tag' not in k.cls]
    goal_line = ps[0].text()
    assert goal_line.startswith('Στόχος: '), (folder, goal_line)
    assert goal_line[len('Στόχος: '):] == meta['goal'], folder
    intro = next(p for p in ps[1:] if p.attrs.get('id') != 'progress')
    # navigation: prev / next link labels
    navs = [k for k in main.kids if isinstance(k, Node) and k.tag == 'nav']
    next_label = None
    for a in iter_tag(navs[-1], 'a'):
        if 'Επόμενο' in a.text() and a.text() != 'Επόμενο μάθημα →': next_label = ws(a.text())

    # raw exercise sections: slice from the source text so the markup stays verbatim
    raw_ex = re.findall(r'<section class="card exercise">.*?</section>', html, re.S)
    body = []
    ex_i = 0
    downloads = []
    for sec in (k for k in main.kids if isinstance(k, Node) and k.tag == 'section'):
        if 'exercise' in sec.cls:
            body.append(raw_ex[ex_i]); ex_i += 1
        else:
            body.append('\n\n'.join(blocks(sec)))
        for a in iter_tag(sec, 'a'):
            h = a.attrs['href']
            if h.startswith('../adult-materials/') and h not in downloads: downloads.append(h)
    assert ex_i == len(raw_ex)
    # sections: heading blocks must start with '##' for md structure; eyebrow para precedes heading
    body_md = '\n\n'.join(body) + '\n'
    dl = [d.replace('..', '', 1) for d in downloads]

    # teacher page
    tmain = find(parse(thtml), 'main')
    th = find(tmain, 'header')
    tps = [k for k in th.kids if isinstance(k, Node) and k.tag == 'p' and 'tag' not in k.cls]
    ttag = next(k for k in th.kids if isinstance(k, Node) and ('tag' in k.cls or 'eyebrow' in k.cls))
    tblocks = []
    for sec in (k for k in tmain.kids if isinstance(k, Node) and k.tag == 'section'):
        tblocks += blocks(sec)
    teacher = '\n\n'.join(tblocks)

    fields = [('number', num), ('slug', folder.name), ('title', meta['title']), ('goal', meta['goal']),
              ('minutes', meta['minutes']), ('optional', meta['optional']),
              ('exercise', EXERCISES.get(num)), ('downloads', dl),
              ('tag', ttag_text(tagel)), ('intro', ws(intro.text())),
              ('teacher_tag', ttag_text(ttag)), ('teacher_title', ws(find(th, 'h1').text())),
              ('teacher_goal', ws(tps[0].text()))]
    if next_label: fields.append(('next_label', next_label))
    return fields, body_md, teacher

def ttag_text(n): return ws(n.text())

# ---------------------------------------------------------------- guide
def convert_guide():
    html = (SRC / 'adults/teacher-guide.html').read_text(encoding='utf-8')
    main = find(parse(html), 'main')
    tag = next(k for k in main.kids if isinstance(k, Node) and k.tag == 'p' and 'tag' in k.cls)
    h1 = find(main, 'h1')
    intro = next(k for k in main.kids if isinstance(k, Node) and k.tag == 'p' and 'tag' not in k.cls)
    body = []
    for sec in (k for k in main.kids if isinstance(k, Node) and k.tag == 'section'):
        body.append('\n\n'.join(blocks(sec)))
    fields = [('title', ws(h1.text())), ('tag', ws(tag.text())), ('intro', ws(intro.text()))]
    return frontmatter(fields) + '\n' + '\n\n'.join(body) + '\n'

# ---------------------------------------------------------------- assets
LESSON1_RESET = '''
/* --- added by site/scripts/convert_adults.py: lesson 1 "Ξεκινώ ξανά" button (was an inline script) --- */
const resetButton = document.getElementById('reset');
if (resetButton) resetButton.addEventListener('click', () => {
  steps.forEach(x => { x.checked = false; });
  updateProgress();
  window.scrollTo({top: 0, behavior: 'smooth'});
});
'''
CSS_EXTRA = '''
/* --- added by site/scripts/convert_adults.py: styles lesson 1 had inline --- */
.eyebrow{color:#365b50;font-weight:bold;font-size:.85rem}.muted{color:#52636d}
kbd{font:inherit;background:#edf1f4;border:1px solid #aab9c2;border-radius:4px;padding:1px 7px;white-space:nowrap}
'''

def copy_assets():
    dst = SITE / 'public/adult-materials'; dst.mkdir(parents=True, exist_ok=True)
    for name in ('lessons.js', 'lessons.css', 'programma-ergasias.pdf', 'paketo-exaskisis.zip'):
        shutil.copyfile(SRC / 'adult-materials' / name, dst / name)
    # lesson 1's checkboxes have no class="step"; lessons.js only handles .step, so lesson 1 markup is
    # converted to the same `- [ ]` convention and the layout renders class="step" for all lessons.
    with open(dst / 'lessons.js', 'a', encoding='utf-8') as f: f.write(LESSON1_RESET)
    with open(dst / 'lessons.css', 'a', encoding='utf-8') as f: f.write(CSS_EXTRA)

def main():
    OUT.mkdir(parents=True, exist_ok=True); OUT_GUIDE.mkdir(parents=True, exist_ok=True)
    n = 0
    for folder in sorted(SRC.glob('adult-lesson-*')):
        fields, body, teacher = convert_lesson(folder)
        name = folder.name.replace('adult-lesson-', '') + '.md'
        (OUT / name).write_text(frontmatter(fields, teacher) + '\n' + body, encoding='utf-8'); n += 1
    (OUT_GUIDE / 'teacher-guide.md').write_text(convert_guide(), encoding='utf-8')
    copy_assets()
    print(f'wrote {n} lessons, 1 guide, assets')

if __name__ == '__main__':
    main()
