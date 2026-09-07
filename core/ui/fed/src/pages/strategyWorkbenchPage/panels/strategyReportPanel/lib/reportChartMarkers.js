/**
 * 报告图买卖/机会标记：圆角 pin（与价格 K 线共用）。
 * 尖端朝上贴在线下方，尖端朝下贴在线上方。
 */

export const REPORT_MARKER_PIN_UP = 'path://M6,0 L1,9 C1,13 3.5,15 6,15 C8.5,15 11,13 11,9 L6,0 Z';
export const REPORT_MARKER_PIN_DOWN = 'path://M6,15 L1,6 C1,2 3.5,0 6,0 C8.5,0 11,2 11,6 L6,15 Z';
export const REPORT_MARKER_PIN_SIZE = 14;
export const REPORT_MARKER_PIN_OFFSET_UP = 12;
export const REPORT_MARKER_PIN_OFFSET_DOWN = -12;

export function reportMarkerPinStyle(color, shadowRgb) {
  return {
    color,
    borderColor: '#FFFFFF',
    borderWidth: 2,
    shadowBlur: 10,
    shadowColor: `rgba(${shadowRgb}, 0.72)`,
    shadowOffsetY: 1,
  };
}
