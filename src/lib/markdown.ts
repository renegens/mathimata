import { createMarkdownProcessor } from '@astrojs/markdown-remark';
import rehypeSite from '../plugins/rehype-site.mjs';

const BASE = import.meta.env.BASE_URL.endsWith('/') ? import.meta.env.BASE_URL : import.meta.env.BASE_URL + '/';
const processors = new Map<string, Awaited<ReturnType<typeof createMarkdownProcessor>>>();

/** Render a Markdown string kept in frontmatter (e.g. adults `teacher`) with the same plugin as page bodies. */
export async function renderMarkdown(source: string, mode: 'adults' | 'cards' | 'plain' = 'adults', frontmatter: Record<string, unknown> = {}) {
  let p = processors.get(mode);
  if (!p) {
    p = await createMarkdownProcessor({ rehypePlugins: [[rehypeSite, { base: BASE, mode }]] });
    processors.set(mode, p);
  }
  const { code } = await p.render(source, { frontmatter });
  return code;
}
