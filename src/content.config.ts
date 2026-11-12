import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const sitePath = z.string().startsWith('/');
const link = z.object({ label: z.string().min(1), href: z.string().min(1) }).strict();
const md = (name: string) => glob({ pattern: '*.md', base: `./src/content/${name}` });

const adults = defineCollection({
  loader: md('adults'),
  schema: z.object({
    number: z.number().int().min(1),
    slug: z.string().regex(/^adult-lesson-\d\d-[a-z0-9-]+$/),
    title: z.string().min(1),
    goal: z.string().min(1),
    minutes: z.number().int().positive(),
    optional: z.boolean(),
    exercise: z.enum(['note-app', 'practice-form', 'email-form', 'typing', 'copy-paste', 'quiz', 'draft', 'calendar', 'stock']).nullable(),
    downloads: z.array(sitePath),
    tag: z.string(),
    intro: z.string(),
    teacher_tag: z.string(),
    teacher_title: z.string(),
    teacher_goal: z.string(),
    teacher: z.string().min(1),
    next_label: z.string().optional(),
  }).strict(),
});

const adultsGuide = defineCollection({
  loader: md('adults-guide'),
  schema: z.object({ title: z.string(), tag: z.string(), intro: z.string() }).strict(),
});

const scratchPages = defineCollection({
  loader: md('scratch-pages'),
  schema: z.object({
    id: z.enum(['games-index', 'lessons-index', 'course-index']),
    url: sitePath,
    html_title: z.string(),
    title: z.string(),
    tag: z.string(),
    back: link,
    lede: z.string().optional(),
    intro: z.string().optional(),
    promos: z.array(z.object({ heading: z.string(), text: z.string(), cta_label: z.string(), cta_href: sitePath }).strict()).optional(),
    download_all: link,
    teacher_notes: link.optional(),
    pages: z.array(link).optional(),
    sections: z.array(z.object({ id: z.enum(['lessons', 'starters', 'games']), heading: z.string(), intro: z.string() }).strict()).optional(),
  }).strict(),
});

const scratchGames = defineCollection({
  loader: md('scratch-games'),
  schema: z.object({
    number: z.number().int(), slug: z.string(), title: z.string(), description: z.string(),
    icon: sitePath, sb3: sitePath, assets_zip: sitePath,
  }).strict(),
});

const scratchLessons = defineCollection({
  loader: md('scratch-lessons'),
  schema: z.object({
    number: z.number().int(), slug: z.string(), title: z.string(), concept: z.string(), goal: z.string(),
    minutes: z.number().int(), start: z.string(),
    starter: sitePath, complete: sitePath, assets_zip: sitePath, preview: sitePath,
    reference: z.object({ label: z.string(), url: z.string().url() }).strict(),
    footnote: z.string(), html_title: z.string(), teacher_page: sitePath,
  }).strict(),
});

const scratchLessonTeacher = defineCollection({
  loader: md('scratch-lesson-teacher'),
  schema: z.object({
    lesson: z.string(), number: z.number().int(), title: z.string(), html_title: z.string(), student_page: sitePath,
  }).strict(),
});

const scratchCourse = defineCollection({
  loader: md('scratch-course'),
  schema: z.discriminatedUnion('kind', [
    z.object({
      kind: z.literal('lesson'), number: z.number().int().min(1), slug: z.string().regex(/^lesson-\d+$/),
      title: z.string(), goal: z.string(), status: z.enum(['full', 'outline']), minutes: z.number().int(),
      ages: z.string(), download: sitePath.optional(), html_title: z.string(),
    }).strict(),
    z.object({
      kind: z.literal('page'), slug: z.enum(['roadmap', 'quick-reference', 'checklist']),
      title: z.string(), download: sitePath, html_title: z.string(),
    }).strict(),
  ]),
});

const scratchCourseGames = defineCollection({
  loader: md('scratch-course-games'),
  schema: z.object({
    order: z.number().int(), slug: z.string(), title: z.string(), description: z.string(),
    concepts: z.array(z.string()), file: sitePath, screenshot: sitePath,
    author: z.string(), license: z.string(), license_file: sitePath,
  }).strict(),
});

const scratchCourseStarters = defineCollection({
  loader: md('scratch-course-starters'),
  schema: z.object({
    order: z.number().int(), slug: z.string(), title: z.string(), description: z.string(),
    file: sitePath, author: z.string(),
  }).strict(),
});

const microbit = defineCollection({
  loader: md('microbit'),
  schema: z.object({
    slug: z.enum(['emojis', 'teacher-notes']), url: sitePath, html_title: z.string(), title: z.string(), tag: z.string(),
    lead: z.string().optional(), intro: z.string(),
    nav: z.array(link), footer_back: link.optional(),
    scripts: z.array(sitePath).default([]), stylesheets: z.array(sitePath).default([]),
    downloads: z.array(link).default([]), teacher_page: sitePath.optional(),
    designer: z.string().optional(),
  }).strict(),
});

export const collections = {
  adults, 'adults-guide': adultsGuide, 'scratch-pages': scratchPages, 'scratch-games': scratchGames,
  'scratch-lessons': scratchLessons, 'scratch-lesson-teacher': scratchLessonTeacher,
  'scratch-course': scratchCourse, 'scratch-course-games': scratchCourseGames,
  'scratch-course-starters': scratchCourseStarters, microbit,
};
