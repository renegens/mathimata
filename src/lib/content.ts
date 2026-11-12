import { getCollection, getEntry, type CollectionEntry } from 'astro:content';

export async function adultLessons(): Promise<CollectionEntry<'adults'>[]> {
  return (await getCollection('adults')).sort((a, b) => a.data.number - b.data.number);
}
export async function courseLessons() {
  const all = await getCollection('scratch-course');
  return all
    .filter((e): e is CollectionEntry<'scratch-course'> & { data: { kind: 'lesson' } } => e.data.kind === 'lesson')
    .sort((a, b) => a.data.number - b.data.number);
}
export async function scratchLessons() {
  return (await getCollection('scratch-lessons')).sort((a, b) => a.data.number - b.data.number);
}
export { getEntry, getCollection };
