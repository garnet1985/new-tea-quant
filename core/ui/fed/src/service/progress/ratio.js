/** 进度文件的显示比例。(已完成步骤 + 当前子步骤) / 总步骤。 */
export function progressRatio(step, stepTotal, sub = 0, subTotal = 0) {
  const total = Number(stepTotal);
  if (!Number.isFinite(total) || total <= 0) return 0;
  const done = Math.min(Math.max(Number(step) || 0, 0), total);
  const innerTotal = Number(subTotal);
  const inner = Number.isFinite(innerTotal) && innerTotal > 0
    ? Math.min(Math.max(Number(sub) || 0, 0), innerTotal) / innerTotal
    : 0;
  return Math.max(0, Math.min(1, (done + inner) / total));
}
