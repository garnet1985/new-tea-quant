/** 与 ``settings.analysis`` 对齐（回测后归因；不进 execute_fp） */
export function buildStrategyAnalysisSchema({ mlInstalled = false } = {}) {
  return {
    name: 'strategyAnalysis',
    type: 'fieldGroup',
    label: '',
    children: [
      {
        name: 'analysis.enabled',
        label: '回测后归因',
        tooltip: mlInstalled
          ? '回测写完报告后，在报告下方生成归因解读。不进入版本指纹，改此项不必重跑枚举。'
          : '需要先安装机器学习依赖（XGBoost / SHAP）才能开关。',
        type: 'switch',
        readonly: !mlInstalled,
      },
    ],
  };
}

const strategyAnalysisSchema = buildStrategyAnalysisSchema();

export default strategyAnalysisSchema;
