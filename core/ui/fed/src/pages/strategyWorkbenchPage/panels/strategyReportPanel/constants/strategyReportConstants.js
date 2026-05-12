/** 报告 Tab 定义（与后端 ``available_tabs`` / 执行步骤 key 对齐） */
export const STEP_TABS = [
  { key: 'enum', label: '枚举报告' },
  { key: 'price', label: '价格回测报告' },
  { key: 'capital', label: '资金模拟报告' },
];

/** 对比版本下拉末项：打开完整版本列表 */
export const REPORT_COMPARE_MORE_MENU_VALUE = '__report_compare_more_versions__';

/** 报告对比弹窗右侧：未选其它快照版本 */
export const COMPARE_EMPTY_OTHER_VERSION_ZH = '无可对比结果，请选择不同版本';
/** 报告对比弹窗右侧：已选版本但该 Tab 无可用报告数据 */
export const COMPARE_NO_REPORT_FOR_SNAPSHOT_ZH = '无可对比结果，没有可用的报告，请使用相应版本生成报告后再试';
