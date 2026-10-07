/**
 * 中性 pin 几何（业务颜色 / 文案由 adapter 注入）。
 */

export const MARKET_MARKER_PIN_UP = 'path://M6,0 L1,9 C1,13 3.5,15 6,15 C8.5,15 11,13 11,9 L6,0 Z';
export const MARKET_MARKER_PIN_DOWN = 'path://M6,15 L1,6 C1,2 3.5,0 6,0 C8.5,0 11,2 11,6 L6,15 Z';
export const MARKET_MARKER_PIN_SIZE = 14;
export const MARKET_MARKER_PIN_OFFSET_UP = 12;
export const MARKET_MARKER_PIN_OFFSET_DOWN = -12;

export function marketMarkerPinStyle(color, shadowRgb) {
  return {
    color,
    borderColor: '#FFFFFF',
    borderWidth: 2,
    shadowBlur: 10,
    shadowColor: `rgba(${shadowRgb}, 0.72)`,
    shadowOffsetY: 1,
  };
}
