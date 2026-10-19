import React, { useEffect, useMemo, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import LoadingBars from 'views/loadingBars';

const STEPS_CREATE = [
  '新茶正在理解你的需求...',
  '正在努力创建策略中...',
  '正在写入策略文件...',
  '正在校验策略配置...',
  '新茶正在努力总结中...',
];

const STEPS_BACKTEST = [
  '新茶正在理解你的需求...',
  '正在调整策略参数...',
  '策略正在回测中...',
  '正在读取回测报告...',
  '新茶正在努力总结中...',
];

const STEPS_SCAN = [
  '新茶正在理解你的需求...',
  '正在准备扫描任务...',
  '机会扫描进行中...',
  '正在整理扫描结果...',
  '新茶正在努力总结中...',
];

const STEPS_ASK = [
  '新茶正在联络喵星，请稍等...',
  '正在组织回答...',
];

const STEPS_DEFAULT = [
  '新茶正在联络喵星，请稍等...',
  '正在准备执行步骤...',
  '本机工具运行中...',
  '正在核对结果...',
  '新茶正在努力总结中...',
];

/**
 * 按用户原话猜一条进度文案轨道（尚无后端逐步推送时的前端分段）。
 * @param {string} userText
 * @param {'ask'|'work'} kind
 */
export function resolvePendingSteps(userText, kind = 'work') {
  if (kind === 'ask') return STEPS_ASK;
  const text = String(userText || '');
  if (/扫描|选股|机会/.test(text)) return STEPS_SCAN;
  if (/回测|重跑|再跑|归因|均线|参数|改成|变成/.test(text)) return STEPS_BACKTEST;
  if (/创建|新建|写(一个)?策略|生成策略|建(一个)?策略/.test(text)) return STEPS_CREATE;
  return STEPS_DEFAULT;
}

/**
 * 进行中气泡：按间隔切换分段文案。
 */
function PendingStream({ userText = '', kind = 'work', onTick }) {
  const steps = useMemo(() => resolvePendingSteps(userText, kind), [userText, kind]);
  const intervalMs = kind === 'ask' ? 2400 : 3800;
  const [index, setIndex] = useState(0);
  const onTickRef = useRef(onTick);
  onTickRef.current = onTick;

  useEffect(() => {
    setIndex(0);
  }, [userText, kind]);

  useEffect(() => {
    onTickRef.current?.();
  }, [index]);

  useEffect(() => {
    if (index >= steps.length - 1) return undefined;
    const timer = window.setTimeout(() => {
      setIndex((value) => Math.min(value + 1, steps.length - 1));
    }, intervalMs);
    return () => window.clearTimeout(timer);
  }, [index, intervalMs, steps.length]);

  const label = steps[Math.min(index, steps.length - 1)] || STEPS_DEFAULT[0];

  return (
    <div className="ntq-assistant-dock__waiting" role="status" aria-live="polite">
      <LoadingBars barCount={4} className="ntq-loading-bars--sm" aria-label={label} />
      <span className="ntq-assistant-dock__waiting-text">{label}</span>
    </div>
  );
}

PendingStream.propTypes = {
  userText: PropTypes.string,
  kind: PropTypes.oneOf(['ask', 'work']),
  onTick: PropTypes.func,
};

export default PendingStream;
