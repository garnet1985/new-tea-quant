/**
 * 报告槽位：从 V2-08 ``result_report`` 按 Tab 取槽位。
 */

/** UI Tab key → ``result_report`` 槽位键 */
export const TAB_TO_RESULT_REPORT_SLOT = {
  enum: 'enum',
  price: 'price_factor',
  portfolio: 'portfolio',
};

/**
 * @param {object|null|undefined} resultReport V2-08 ``result_report``
 * @param {'enum'|'price'|'portfolio'} tabKey
 */
export function slotFromResultReport(resultReport, tabKey) {
  if (!resultReport || typeof resultReport !== 'object') return null;
  const slotKey = TAB_TO_RESULT_REPORT_SLOT[tabKey];
  if (!slotKey) return null;
  const slot = resultReport[slotKey];
  return slot && typeof slot === 'object' ? slot : null;
}
