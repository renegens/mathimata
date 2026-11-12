# AGENTS.md: lesson library (Astro)

Greek lesson website: adult computer lessons, Scratch (games, lessons, a course for ages 7–9) and micro:bit. Every lesson is a Markdown file; Astro builds static pages with one theme per category.

- Live site: https://renegens.github.io/mathimata/ (GitHub Pages; repo `renegens/mathimata`, branch `main`)
- The same build can also be served at `/` by the classroom server (`../lesson-server/`, LAN only).

## Ground rules

- **The Markdown in `src/content/` is the master copy.** Edit lessons there. The old Python generators in `../lesson-server/tools/` and the one-off conversion scripts (archived in `../site-archive/`) must not be re-run against this site.
- **All visible text is Greek**, short and direct. Product names, file extensions and Scratch tokens may stay as they are. Don't rewrite existing lesson wording unless asked.
- **Never delete files.** Move anything no longer needed to `../site-archive/<same path>` instead.
- **URLs are stable.** Students have bookmarks and printed links. Don't rename slugs or `.html` pages. `scripts/legacy-urls.txt` lists every original URL, and the site check fails if one disappears.
- **Links:** write internal links site-absolute (`/scratch-games/...`) or relative. Never hard-code `/mathimata/`; the base path is added at build time.
- **Teacher material is public on purpose**, but it must be clearly labelled («Για εκπαιδευτές» / «Σημειώσεις εκπαιδευτή»). Never add private data (student names, contacts) anywhere in this repo.
- **Third-party files keep their credit:** the course example games are by Jesse Smith (BSD 3-Clause, `public/scratch-games/course/games/LICENSE.txt`), and the course starters come from the Scratch Team (scratch.mit.edu).
- **The site must work offline on a LAN.** No CDN or external font/script requests; fonts come from `@fontsource` packages. Links to scratch.mit.edu etc. in lesson text are fine.
- Don't commit or push unless asked.

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

With `--old ../lesson-server/public` it also compares downloads byte for byte and checks page text against the old site.

## Deploy

A push to `main` runs `.github/workflows/pages.yml`, which runs `npm ci` and builds with `SITE_BASE=/mathimata/`, then deploys to GitHub Pages. Run `npm run check` before pushing.
