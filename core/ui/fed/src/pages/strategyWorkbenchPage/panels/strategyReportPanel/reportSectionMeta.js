/** 回测报告 Accordion 与各 Tab 区块标题 */

export const REPORT_PANEL_TITLE = '回测报告';

export const REPORT_PANEL_TOOLTIP =
  '回测的详细报告会在这里显示，可以点击每个标题后的？来查看结果的详细意义';

export const REPORT_TAB_SECTION_TITLES = {
  enum: '枚举机会报告',
  price: '价格回测报告',
  portfolio: '投资模拟报告',
};

export const ANALYSIS_SECTION_TITLE = '归因解读';

export const ANALYSIS_LOADING_ZH = '正在加载归因报告…';

export const ANALYSIS_ERROR_ZH = '归因报告加载失败';

export const ANALYSIS_MISSING_ZH = '本步尚未生成归因报告。';

export const ANALYSIS_EMPTY_ZH = '这次没有可对比的变化条件。';

export const ANALYSIS_EMPTY_TITLE = '这次还无法归因';

export const ANALYSIS_EMPTY_LEAD_ZH = '可以先核对下面两点：';

export const ANALYSIS_EMPTY_SAMPLE_Q = '是不是样本不够？';

export const ANALYSIS_EMPTY_CAPTURE_Q = '还是没有捕获数据？';

export const ANALYSIS_EMPTY_HIT_BADGE = '更可能是这项';

export function analysisEmptyCaptureDetail({ investmentCount, withSnapshot, isHit }) {
  const n = Number(investmentCount) || 0;
  const snap = Number(withSnapshot) || 0;
  if (isHit) {
    if (snap <= 0) {
      return `本次 ${n} 笔机会里，${snap} 笔记下了现场条件。在命中时用 ctx.capture(名称, 数值) 记下会变化的数字，然后重新跑这一层。`;
    }
    return `记下了 ${snap} 笔现场条件，但没有会变化的数字，无法分档。命中时用 ctx.capture 记下会随行情变化的数值。`;
  }
  if (n <= 0 && snap <= 0) {
    return '这次还看不出有没有记下现场条件，可以对照另一项一起看。';
  }
  return `本次 ${n} 笔机会里，已有 ${snap} 笔记下了现场条件。`;
}

export function analysisEmptySampleDetail({ investmentCount, withSnapshot, isHit }) {
  const n = Number(investmentCount) || 0;
  const snap = Number(withSnapshot) || 0;
  if (isHit) {
    if (n <= 0) {
      return '这一层还没有机会样本。先跑出枚举/回测结果后再看归因。';
    }
    return `有现场条件时，至少需要 2 笔才能分档。本次记下的有效样本是 ${snap} 笔（机会 ${n} 笔）。`;
  }
  if (n <= 0) {
    return '这次还看不出机会样本够不够，可以对照另一项一起看。';
  }
  return `机会数量本身够用（${n} 笔）。`;
}

export const ANALYSIS_CONCLUSION_TITLE = '结论';

export const ANALYSIS_OVERVIEW_TITLE = '这次看什么';

export const ANALYSIS_TIERS_TITLE = '分档对比';

export const ANALYSIS_WATERSHED_TITLE = '分水岭';

export const ANALYSIS_BINS_TITLE = '分档';

export const ANALYSIS_EXPLAIN_CAPTION = '能说明';

export const ANALYSIS_NOT_EXPLAIN_CAPTION = '不能说明';

export const ANALYSIS_OTHER_FIELDS_TITLE = '其它条件';

export const ANALYSIS_MULTIVARIATE_TITLE = '多指标一起看';

export const ANALYSIS_RUN_COMPARISON_TITLE = '版本对照';

export const ANALYSIS_PRIMARY_FIELD_CAPTION = '主条件';

export const ANALYSIS_DIRECTION_CAPTION = '相关方向';

export const ANALYSIS_SIGNIFICANCE_CAPTION = '是否显著';

export const ANALYSIS_SAMPLE_CAPTION = '样本';

export const ANALYSIS_SKIP_CAPTION = '跳过样本';

export const ANALYSIS_TIER_COL_RANGE = '区间';

export const ANALYSIS_TIER_COL_ROI = '平均收益';

export const ANALYSIS_TIER_COL_WIN = '胜率';

export const ANALYSIS_TIER_COL_N = '样本';
