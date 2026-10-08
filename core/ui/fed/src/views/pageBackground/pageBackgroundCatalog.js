/** Served from `public/img/` — not bundled; add filenames here when adding images. */
const PAGE_BACKGROUND_FILES = ['1.jpeg', '2.jpeg', '3.jpeg', '4.jpeg', '5.jpeg', '6.jpeg'];

const PUBLIC_BASE = (process.env.PUBLIC_URL || '').replace(/\/$/, '');

export function pickRandomPageBackgroundUrl() {
  if (PAGE_BACKGROUND_FILES.length === 0) return '';
  const file = PAGE_BACKGROUND_FILES[Math.floor(Math.random() * PAGE_BACKGROUND_FILES.length)];
  return `${PUBLIC_BASE}/img/${file}`;
}
