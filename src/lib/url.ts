// Prefix a site-absolute path ("/scratch-games/") with the configured base.
const BASE = import.meta.env.BASE_URL.replace(/\/$/, '');
export const url = (path: string): string =>
  path.startsWith('/') && !path.startsWith('//') ? BASE + path : path;
export const isExternal = (href: string): boolean => /^https?:\/\//i.test(href);
export const isDownload = (href: string): boolean => /\.(sb3|zip|md|js)$/i.test(href.split(/[?#]/)[0]);
