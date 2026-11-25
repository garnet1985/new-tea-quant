import { renderHelpRichText } from './helpRichText';

describe('renderHelpRichText', () => {
  it('returns plain string unchanged when there are no terms', () => {
    expect(renderHelpRichText('普通说明。')).toBe('普通说明。');
  });

  it('wraps 「term」 segments in highlight spans', () => {
    const parts = renderHelpRichText('先看「严格模式」，再看「演示模式」。');
    expect(Array.isArray(parts)).toBe(true);
    expect(parts[0]).toBe('先看');
    expect(parts[1].props.className).toBe('ntq-global-helper__term');
    expect(parts[1].props.children).toBe('「严格模式」');
    expect(parts[2]).toBe('，再看');
    expect(parts[3].props.children).toBe('「演示模式」');
    expect(parts[4]).toBe('。');
  });
});
