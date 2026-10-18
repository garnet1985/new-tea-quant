/** 进度文件里的 ratio 已经是 0 到 1。显示前只把它收进这个区间。 */
export function progressRatio(ratio) {
  const value = Number(ratio);
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}
