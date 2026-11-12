# AGENTS.md: lesson library (Astro)

Greek lesson website: adult computer lessons, Scratch (games, lessons, a course for ages 7–9) and micro:bit. Every lesson is a Markdown file; Astro builds static pages with one theme per category.

- **Live site:** https://renegens.github.io/mathimata/ (GitHub Pages)
- **Repo:** `renegens/mathimata` (public), branch `main`. **This repo is the only copy of the site.** There is no local server or local source folder any more; clone this repo to work on it.

## History (why things are the way they are)

- The lessons started on a LAN classroom server: a Python static server on port 8765, behind a port-80 systemd socket proxy and firewall rules allowing only the home network. Its pages came from several Python generator scripts.
- In November 2026 the content was converted to Markdown (each converter was checked against the old pages for text and file fidelity) and rebuilt as this Astro site. The redesigned home page has an interactive micro:bit face.
- On 2026-11-12 the classroom server was stopped and fully removed (services disabled, firewall rules deleted). The local working folders, conversion scripts and old generators were moved to the system trash. They are not needed: this repo contains everything the site uses.
- Kept outside the site, never to be published: student lists and contacts. A Python course and a micro:bit sound project were never part of the site and were not carried over.

## Ground rules

- **The Markdown in `src/content/` is the master copy.** Edit lessons there. Never regenerate content from the old HTML site; it no longer exists.
- **All visible text is Greek**, short and direct. Product names, file extensions and Scratch tokens may stay as they are. Don't rewrite existing lesson wording unless asked.
- **Never delete files with `rm`.** If a file must leave the repo, ask first, then move it with `git mv` to an `archive/` folder or into the system trash (`gio trash`). Git history keeps the old version either way.
- **The repo is public:** everything committed is visible to anyone, including teacher notes and Git history. Never commit student names, contact details, credentials or local machine details (paths, IP addresses).
- **URLs are stable.** Students have bookmarks and printed links. Don't rename slugs or `.html` pages. `scripts/legacy-urls.txt` lists every original URL, and the site check fails if one disappears.
- **Links:** write internal links site-absolute (`/scratch-games/...`) or relative. Never hard-code `/mathimata/`; the base path is added at build time.
- **Teacher material is public on purpose**, but it must be clearly labelled («Για εκπαιδευτές» / «Σημειώσεις εκπαιδευτή»).
- **Third-party files keep their credit:** the course example games are by Jesse Smith (BSD 3-Clause, `public/scratch-games/course/games/LICENSE.txt`), and the course starters come from the Scratch Team (scratch.mit.edu).
- **The site is self-contained.** No CDN, analytics, or external font or script requests; fonts come from `@fontsource` packages. This keeps students' visits private and lets the built `dist/` run from any plain static server (e.g. a classroom laptop) without internet. Links to scratch.mit.edu and similar sites in lesson text are fine.
- **Don't commit or push unless asked.** A push to `main` publishes to the live site within about a minute.

## Layout

```
src/content/            lessons (Markdown + YAML frontmatter), one folder per collection
src/content.config.ts   zod schemas: the build fails on wrong/missing frontmatter
src/pages/              routes (mirror the public URLs, incl. `*.html.astro` for .html pages)
src/layouts/            Base + AdultLayout, ScratchLayout, MicrobitLayout
src/components/         SiteBar, LessonList, GameCard
src/styles/             base.css (tokens, light/dark) + home/adults/scratch/microbit themes
src/plugins/rehype-site.mjs   Markdown post-processing (see below)
src/lib/                content helpers, url() (base-aware), markdown rendering
public/                 downloads and scripts, served unchanged at the same path
scripts/check_site.py   built-site checker
scripts/legacy-urls.txt original page URLs that must keep working
astro.config.mjs        SITE_BASE handling + post-build step emitting x.html pages as files
```

## Collections

| Collection | URL | Notes |
|---|---|---|
| `adults/NN-topic.md` (24) | `/<slug>/`, `/<slug>/teacher-notes.html` | `number, slug, title, goal, minutes, optional, exercise, downloads[], tag, intro, teacher_tag, teacher_title, teacher_goal, teacher` (Markdown) + optional `next_label` |
| `adults-guide/teacher-guide.md` | `/adults/teacher-guide.html` | 20-hour sequence; `title, tag, intro` |
| `scratch-pages/*.md` (3) | `/scratch-games/`, `/scratch-games/lessons/`, `/scratch-games/course/` | landing-page text, promos, buttons |
| `scratch-games/*.md` (3) | cards on `/scratch-games/` | `number, slug, title, description, icon, sb3, assets_zip` |
| `scratch-lessons/NN-slug.md` (8) | `/scratch-games/lessons/<slug>/` | `number, slug, title, concept, goal, minutes, start, starter, complete, assets_zip, preview, reference{label,url}, footnote, html_title, teacher_page` |
| `scratch-lesson-teacher/<slug>.md` (8) | `/scratch-games/lessons/<slug>/teacher.html` | `lesson, number, title, html_title, student_page` |
| `scratch-course/*.md` | `/scratch-games/course/lesson-N.html`, `roadmap.html`, `quick-reference.html`, `checklist.html` | `kind: lesson` (`number, title, goal, status: full\|outline, minutes, ages, download`) or `kind: page` |
| `scratch-course-games/*.md` (5), `scratch-course-starters/*.md` (4) | cards on the course page | `order, slug, title, description, file, …`; games also `concepts[], screenshot, author, license` |
| `microbit/emojis.md`, `teacher-notes.md` | `/microbit-emojis/`, `/microbit-emojis/teacher-notes.html` | text + raw HTML for the LED designer |

`src/content.config.ts` has the exact schemas. Copy a neighbouring file when adding a new one.

### Adding a lesson
1. Add `src/content/<collection>/<file>.md` with the same frontmatter as its neighbours. Lists, numbering, prev/next and the sidebar update automatically.
2. Put its downloads in `public/` at the path the lesson links to.
3. Adult lessons: the URL is `/<slug>/`, so use `slug: adult-lesson-NN-topic`.
4. Run `npm run check`.

### Markdown conventions (handled by `rehype-site.mjs`)
- Root-relative links/assets get the base path. External links open in a new tab. `.sb3 .zip .md .js` links get `download`.
- `- [ ] text` becomes a real checkbox. In adult lessons it is `<label class="done"><input class="step">`, which `lessons.js` counts for the progress line.
- Adult lessons: each `##` becomes a card, `> text` becomes a help note, and the «Λήψη PDF / Άνοιγμα PDF» list becomes buttons from `downloads`.
- Wide tables scroll inside a wrapper.
- **Interactive blocks are raw HTML; keep their ids and data attributes unchanged:**
  - Adult exercises are `<section class="card exercise">` blocks driven by `public/adult-materials/lessons.js`. The exercise ids are `note-app` (2), `practice-form` (6), `email-form` (7), `typing` (8), `copy-paste` (9), `quiz` (11, 15), `draft` (12, 18, 19), `calendar` (16) and `stock` (17).
  - The micro:bit designer (`#led-grid`, `button[data-pattern]`, `#led-status`, `#pattern-output`) is driven by `public/microbit-emojis/lesson.js`. Don't put blank lines inside these blocks.

## Themes

The tokens live in `src/styles/base.css`, with light and dark variants. Each category has its own stylesheet:

| Category | Style |
|---|---|
| Home | Neutral page with three category cards |
| Adults | Noto Sans, 20px body, high contrast, numbered steps, lesson sidebar; teacher pages in a purple accent |
| Scratch | Comfortaa headings, bright rounded cards, big buttons; teacher pages in teal |
| micro:bit | Scratch base plus an LED/red accent and mono labels |

Keep text contrast at 4.5:1 or better, keep focus rings visible, avoid horizontal scrolling at 390px, and keep the print styles.

## Commands

```sh
npm ci                 # Node 22
npm run dev            # http://localhost:4321/
npm run build          # dist/ (base /)
npm run build:pages    # dist-mathimata/ (base /mathimata/)
npm run preview        # serve dist/
npm run check          # astro check + both builds + scripts/check_site.py on each
```

`check_site.py DIST --base B` checks:
- every URL in `legacy-urls.txt` exists
- every internal link, asset and CSS `url()` resolves under the base

Its `--old DIR` option compared the build with the retired classroom site during the migration; that folder no longer exists, so leave the option unused.

For visual checks, take headless screenshots of `npm run preview` at 390px and 1280px wide, in both light and dark mode:

```sh
chromium --headless --screenshot=out.png --window-size=390,3000 http://127.0.0.1:4321/
chromium --headless --screenshot=out-dark.png --window-size=1280,1500 --blink-settings=preferredColorScheme=0 http://127.0.0.1:4321/
```

## Workflow: making a change

```sh
git clone https://github.com/renegens/mathimata.git && cd mathimata
npm ci
npm run dev                      # edit src/content/*.md, watch http://localhost:4321/
npm run check                    # must pass before committing
git add -A && git commit -m "…" && git push   # only when the user asks
```

## Deploy

- A push to `main` (or a manual run) triggers `.github/workflows/pages.yml`. It runs `npm ci`, then `npm run build` with `SITE_BASE=/mathimata/`, then deploys to GitHub Pages.
- The workflow's GitHub Actions run on Node 24 (`checkout@v7`, `setup-node@v7`, `upload-pages-artifact@v5`, `deploy-pages@v5`). The site itself builds with Node 22. When GitHub warns about deprecated runtimes, bump the action majors.
- Pages is configured with `build_type=workflow`; the `gh-pages` branch isn't used.
- **Verify a deploy:**
  - Watch the run: `gh run watch <id> -R renegens/mathimata --exit-status` (get the id from `gh run list -R renegens/mathimata -L 1`).
  - Check that every legacy URL answers 200 on the live site: loop over `scripts/legacy-urls.txt`, URL-encode each path and drop a trailing `index.html` before requesting it.
  - Only one deploy runs at a time; a newer run cancels an older one, so a "cancelled" run is normal.
