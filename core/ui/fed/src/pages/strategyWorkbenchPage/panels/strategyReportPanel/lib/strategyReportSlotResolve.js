/**
 * 报告槽位：V2-07 ``stepReportSlots`` 优先，其次工作台 ``result_report`` 快照摘要。
 */

export function resolveStepReportSlot(step, stepReportSlots) {
  if (!step || !stepReportSlots || typeof stepReportSlots !== 'object') return null;
  const slot = stepReportSlots[step];
  return slot && typeof slot === 'object' ? slot : null;
}

export function resolveEnumReportSlot({ stepReportSlots, snapshotSlot }) {
  return (
    resolveStepReportSlot('enum', stepReportSlots)
    || (snapshotSlot && typeof snapshotSlot === 'object' ? snapshotSlot : null)
    || null
  );
}

export function resolvePriceReportSlot({ stepReportSlots, snapshotSlot }) {
  return (
    resolveStepReportSlot('price', stepReportSlots)
    || (snapshotSlot && typeof snapshotSlot === 'object' ? snapshotSlot : null)
    || null
  );
}

export function resolveCapitalReportSlot({ stepReportSlots, snapshotSlot }) {
  return (
    resolveStepReportSlot('capital', stepReportSlots)
    || (snapshotSlot && typeof snapshotSlot === 'object' ? snapshotSlot : null)
    || null
  );
}

/** 对比侧：仅 V2-07 单步 report 槽位。 */
export function resolveEnumReportSlotForCompare(slot) {
  return slot && typeof slot === 'object' ? slot : null;
}

export function resolvePriceReportSlotForCompare(slot) {
  return slot && typeof slot === 'object' ? slot : null;
}

export function resolveCapitalReportSlotForCompare(slot) {
  return slot && typeof slot === 'object' ? slot : null;
}
