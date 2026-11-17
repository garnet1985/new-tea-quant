import { useId } from 'react';

/**
 * 稳定、可作 DOM id 的控件 id（去掉 React useId 里的冒号，避免 querySelector / 审计误报）。
 * @param {string} [id]
 */
export default function useControlId(id = '') {
  const auto = useId().replace(/:/g, '');
  return id || `ntq-${auto}`;
}
