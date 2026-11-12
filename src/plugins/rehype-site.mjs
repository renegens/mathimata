// rehype plugin: re-applies what Markdown lost and makes links work under any base path.
//  - prefixes root-relative URLs (href/src starting with "/") with the site base
//  - external links open in a new tab (target=_blank rel=noopener)
//  - download attribute for .sb3/.zip/.md/.js links
//  - task list items become <label><input type=checkbox> ...</label> (adults: class "done" + "step", which lessons.js binds to)
//  - adults: "## heading + content" groups become <section class="card">; "> note" becomes <p class="help">;
//    the two-item "Λήψη PDF / Άνοιγμα PDF" list becomes download buttons (href comes from frontmatter `downloads`)
//  - tables get a scroll wrapper so wide tables never make the page scroll sideways
import { visit } from 'unist-util-visit';

const DOWNLOAD_EXT = /\.(sb3|zip|md|js)$/i;

const el = (tagName, properties = {}, children = []) => ({ type: 'element', tagName, properties, children });
const text = (value) => ({ type: 'text', value });
const textOf = (node) =>
  node.type === 'text' ? node.value : (node.children || []).map(textOf).join('');
const cls = (node) => {
  const c = node.properties?.className;
  return Array.isArray(c) ? c : c ? String(c).split(/\s+/) : [];
};
const isEl = (n, name) => n && n.type === 'element' && (!name || n.tagName === name);

export function withBase(base, url) {
  if (typeof url !== 'string') return url;
  if (url.startsWith('/') && !url.startsWith('//')) return base.replace(/\/$/, '') + url;
  return url;
}

export default function rehypeSite(options = {}) {
  const base = options.base || '/';
  return (tree, file) => {
    const path = String(file?.path || '').replaceAll('\\', '/');
    const fm = file?.data?.astro?.frontmatter || {};
    const mode =
      options.mode ||
      (/\/content\/adults(-guide)?\//.test(path) ? 'adults'
        : /\/content\/scratch-lesson(s|-teacher)\//.test(path) ? 'cards'
        : 'plain');
    const adults = mode === 'adults';
    const cards = mode === 'adults' || mode === 'cards';

    // 1. Base prefix, external links, download attribute
    visit(tree, (node) => {
      if (node.type === 'raw') {
        node.value = node.value.replace(/\b(href|src)="\/(?!\/)/g, `$1="${base.replace(/\/$/, '')}/`);
        return;
      }
      if (node.type !== 'element') return;
      const p = node.properties || (node.properties = {});
      for (const attr of ['href', 'src']) if (typeof p[attr] === 'string') p[attr] = withBase(base, p[attr]);
      if (node.tagName === 'a' && typeof p.href === 'string') {
        const href = p.href;
        if (/^https?:\/\//i.test(href)) {
          p.target = '_blank';
          p.rel = 'noopener';
        } else if (DOWNLOAD_EXT.test(href.split(/[?#]/)[0]) && p.download === undefined) {
          p.download = true;
        }
      }
    });

    // 2. Task list items
    visit(tree, 'element', (node, index, parent) => {
      if (node.tagName !== 'li' || !cls(node).includes('task-list-item')) return;
      const kids = [];
      let input = null;
      const flatten = (nodes) => {
        for (const c of nodes) {
          if (isEl(c, 'input') && c.properties?.type === 'checkbox') input = c;
          else if (isEl(c, 'p')) flatten(c.children);
          else kids.push(c);
        }
      };
      flatten(node.children);
      if (!input) return;
      delete input.properties.disabled;
      if (adults) input.properties.className = ['step'];
      const label = el('label', { className: adults ? ['done'] : ['task'] }, [input, ...kids]);
      // trim the whitespace GFM puts after the checkbox for the adult markup lessons.js was built with
      if (kids[0] && kids[0].type === 'text') kids[0].value = kids[0].value.replace(/^\s+/, '');
      node.children = [label];
      node.properties.className = ['task-item'];
    });

    visit(tree, 'element', (node) => {
      if (node.tagName === 'ul' && cls(node).includes('contains-task-list')) {
        node.properties.className = ['checks'];
      }
    });

    // 3. Adult-specific rewrites
    if (adults) {
      const pdf = (fm.downloads || []).find((d) => /\.pdf$/i.test(d));
      visit(tree, 'element', (node, index, parent) => {
        if (!parent || index == null) return;
        if (node.tagName === 'blockquote') {
          const paras = node.children.filter((c) => isEl(c, 'p'));
          if (paras.length === 1 && node.children.every((c) => isEl(c, 'p') || (c.type === 'text' && !c.value.trim()))) {
            parent.children[index] = el('p', { className: ['help'] }, paras[0].children);
          }
        }
        if (node.tagName === 'ul' && pdf) {
          const items = node.children.filter((c) => isEl(c, 'li')).map((li) => textOf(li).trim());
          if (items.length === 2 && items[0] === 'Λήψη PDF' && items[1] === 'Άνοιγμα PDF (νέα καρτέλα)') {
            const href = withBase(base, pdf);
            parent.children[index] = el('div', { className: ['bar'] }, [
              el('a', { className: ['button'], href, download: true }, [text(items[0])]),
              el('a', { className: ['button', 'secondary'], href, target: '_blank', rel: 'noopener' }, [text(items[1])]),
            ]);
          }
        }
      });
    }

    // 4. Tables get a scroll wrapper
    visit(tree, 'element', (node, index, parent) => {
      if (node.tagName === 'table' && parent && index != null && !(isEl(parent, 'div') && cls(parent).includes('table-wrap'))) {
        parent.children[index] = el('div', { className: ['table-wrap'] }, [node]);
        return 'skip';
      }
    });

    // 5. Group "h2 + following blocks" into card sections (top level only)
    if (cards) {
      const out = [];
      let group = null;
      const close = () => { group = null; };
      for (const node of tree.children) {
        if (isEl(node, 'h2')) {
          group = el('section', { className: ['card'] }, [node]);
          out.push(group);
        } else if (isEl(node, 'section')) {
          close();
          out.push(node);
        } else if (group) {
          if (node.type === 'text' && !node.value.trim()) continue;
          group.children.push(node);
        } else out.push(node);
      }
      tree.children = out;
    }
  };
}
