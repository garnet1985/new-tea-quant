export const HELP_TARGET_ATTR = 'data-ntq-help';
export const HELP_TARGET_WAIT_MS = 1500;
const HOLE_PAD = 8;
const VIEW_PAD = 16;
const HOLE_GAP = 14;

export function queryHelpTarget(target) {
  const id = String(target || '').trim();
  if (!id || typeof document === 'undefined') return null;
  const el = document.querySelector(`[${HELP_TARGET_ATTR}="${id}"]`);
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) return null;
  return el;
}

export function measureHole(el, padding = HOLE_PAD) {
  const rect = el.getBoundingClientRect();
  return {
    left: Math.max(0, rect.left - padding),
    top: Math.max(0, rect.top - padding),
    width: rect.width + padding * 2,
    height: rect.height + padding * 2,
  };
}

function nextFrame() {
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => resolve());
  });
}

export async function resolveLiveSteps(steps, timeoutMs = HELP_TARGET_WAIT_MS) {
  const list = Array.isArray(steps) ? steps : [];
  const deadline = Date.now() + Math.max(0, Number(timeoutMs) || 0);
  const pick = () => list.filter((step) => queryHelpTarget(step?.target));
  let live = pick();
  while (!live.length && Date.now() < deadline) {
    await nextFrame();
    live = pick();
  }
  return live;
}

export function placeCard(hole, card, viewport) {
  const vw = Number(viewport?.width) || 0;
  const vh = Number(viewport?.height) || 0;
  const cw = Math.max(1, Number(card?.width) || 360);
  const ch = Math.max(1, Number(card?.height) || 200);
  const clampX = (x) => Math.min(Math.max(VIEW_PAD, x), Math.max(VIEW_PAD, vw - cw - VIEW_PAD));
  const clampY = (y) => Math.min(Math.max(VIEW_PAD, y), Math.max(VIEW_PAD, vh - ch - VIEW_PAD));
  if (!hole) return { left: VIEW_PAD, top: VIEW_PAD };

  const right = vw - (hole.left + hole.width);
  const left = hole.left;
  const bottom = vh - (hole.top + hole.height);
  const top = hole.top;

  if (right >= cw + HOLE_GAP + VIEW_PAD) {
    return { left: hole.left + hole.width + HOLE_GAP, top: clampY(hole.top) };
  }
  if (left >= cw + HOLE_GAP + VIEW_PAD) {
    return { left: hole.left - HOLE_GAP - cw, top: clampY(hole.top) };
  }
  if (bottom >= ch + HOLE_GAP + VIEW_PAD) {
    return { left: clampX(hole.left), top: hole.top + hole.height + HOLE_GAP };
  }
  if (top >= ch + HOLE_GAP + VIEW_PAD) {
    return { left: clampX(hole.left), top: hole.top - HOLE_GAP - ch };
  }
  return { left: clampX(VIEW_PAD), top: clampY(VIEW_PAD) };
}

export const GLOBAL_HELPER_SESSION_EVENT = 'ntq-global-helper-session';

export function emitGlobalHelperSession(open) {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(GLOBAL_HELPER_SESSION_EVENT, { detail: { open: Boolean(open) } }));
}
