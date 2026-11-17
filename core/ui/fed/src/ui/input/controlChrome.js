import { INPUT_SURFACE_TOKENS, pickToken } from 'ui/tokens';

/** Input 圆角扩展：默认 sm（现有观感）；none = 直角 */
export const INPUT_RADIUS_TOKENS = ['sm', 'none'];

/**
 * 输入控件 chrome class。
 * surface 始终带 class（solid / glass），便于默认实底与 disabled 对比。
 * @param {{ surface?: string, radius?: string }} opts
 */
export function inputChromeClass({ surface = 'solid', radius = 'sm' } = {}) {
  const surfaceToken = pickToken(surface, INPUT_SURFACE_TOKENS, 'solid');
  const radiusToken = pickToken(radius, INPUT_RADIUS_TOKENS, 'sm');
  return [
    `ntq-input--surface-${surfaceToken}`,
    radiusToken !== 'sm' ? `ntq-input--radius-${radiusToken}` : '',
  ].filter(Boolean).join(' ');
}
