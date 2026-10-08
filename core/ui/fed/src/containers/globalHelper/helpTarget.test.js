import { measureHole, placeCard, queryHelpTarget } from './helpTarget';

describe('placeCard', () => {
  const card = { width: 360, height: 200 };
  const viewport = { width: 1280, height: 800 };

  it('prefers the right side when there is room', () => {
    const pos = placeCard(
      { left: 40, top: 80, width: 280, height: 400 },
      card,
      viewport,
    );
    expect(pos.left).toBeGreaterThan(320);
    expect(pos.top).toBeGreaterThanOrEqual(16);
  });

  it('uses the left side when the hole is on the right', () => {
    const pos = placeCard(
      { left: 900, top: 80, width: 320, height: 200 },
      card,
      viewport,
    );
    expect(pos.left + card.width).toBeLessThan(900);
  });
});

describe('queryHelpTarget / measureHole', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('returns null when the node is missing or has no box', () => {
    expect(queryHelpTarget('design-settings')).toBeNull();
    const empty = document.createElement('div');
    empty.setAttribute('data-ntq-help', 'design-settings');
    document.body.appendChild(empty);
    expect(queryHelpTarget('design-settings')).toBeNull();
  });

  it('measures a padded hole from a visible node', () => {
    const el = document.createElement('div');
    el.setAttribute('data-ntq-help', 'design-execution');
    el.getBoundingClientRect = () => ({
      left: 40,
      top: 60,
      width: 120,
      height: 80,
      right: 160,
      bottom: 140,
    });
    document.body.appendChild(el);
    const found = queryHelpTarget('design-execution');
    expect(found).toBe(el);
    const hole = measureHole(found, 8);
    expect(hole).toEqual({
      left: 32,
      top: 52,
      width: 136,
      height: 96,
    });
  });
});
