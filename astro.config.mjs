import { defineConfig, passthroughImageService } from 'astro/config';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
import rehypeSite from './src/plugins/rehype-site.mjs';

// Base path: "/" locally, "/mathimata/" on GitHub Pages (SITE_BASE env var).
let base = process.env.SITE_BASE || '/';
if (!base.startsWith('/')) base = '/' + base;
if (!base.endsWith('/')) base += '/';

// Pages such as /x/teacher-notes.html must be emitted as that exact file, not as
// teacher-notes.html/index.html (Astro's directory format). Flatten them after the build.
const flattenHtmlRoutes = {
  name: 'flatten-html-routes',
  hooks: {
    'astro:build:done': ({ dir }) => {
      const walk = (d) => {
        for (const e of fs.readdirSync(d, { withFileTypes: true })) {
          if (!e.isDirectory()) continue;
          const p = path.join(d, e.name);
          if (e.name.endsWith('.html')) {
            const tmp = p + '.tmp-flatten';
            fs.renameSync(path.join(p, 'index.html'), tmp);
            fs.rmdirSync(p);
            fs.renameSync(tmp, p);
          } else walk(p);
        }
      };
      walk(fileURLToPath(dir));
    },
  },
};

export default defineConfig({
  integrations: [flattenHtmlRoutes],
  base,
  output: 'static',
  trailingSlash: 'ignore',
  build: { format: 'directory', assets: '_assets' },
  image: { service: passthroughImageService() },
  markdown: { syntaxHighlight: false, rehypePlugins: [[rehypeSite, { base }]] },
  devToolbar: { enabled: false },
});
