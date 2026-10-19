import React, { useEffect, useMemo, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import LoadingBars from 'views/loadingBars';

const STEPS_CREATE = [
  '新茶正在理解你的需求...',
  '正在拼策略骨架...',
  '正在写入策略文件...',
  '正在校验配置有没有穿帮...',
  '新茶正在整理刚才做了什么...',
];

const STEPS_BACKTEST = [
  '新茶正在理解你的需求...',
  '正在核对策略参数...',
  '回测引擎开跑了，稍等片刻...',
  'K 线还在过筛，没卡住...',
  '正在读取回测报告...',
  '新茶正在整理数字...',
];

const STEPS_ATTRIBUTE = [
  '新茶正在理解你的需求...',
  '正在检查归因配置...',
  '对照轴展开中，这一步通常更久...',
  '各档参数还在逐个回放...',
  '正在汇总敏感度...',
  '新茶正在整理归因结论...',
];

const STEPS_SCAN = [
  '新茶正在理解你的需求...',
  '正在准备扫描任务...',
  '机会扫描进行中...',
  '正在整理扫描结果...',
  '新茶正在整理名单...',
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
  '新茶正在整理答复...',
];

/** 主轨道走完后轮换，避免长时间停在同一句。 */
const HOLDING_LINES = [
  '还在算，新茶没有睡着...',
  '这一步比预想久一点，继续盯着...',
  '后台还在干活，不是卡住了...',
  '数字正在排队过安检...',
  '喝口水再等一下，马上就好...',
  '新茶在对账，别眨眼...',
  '进度条在心里，表面上很淡定...',
  '喵星线路有点挤，还在连...',
  '复杂任务需要多炖一会儿...',
  '马上回来，别把我关了...',
];

/**
 * 按用户原话猜一条进度文案轨道（尚无后端逐步推送时的前端分段）。
 * @param {string} userText
 * @param {'ask'|'work'} kind
 */
export function resolvePendingSteps(userText, kind = 'work') {
  if (kind === 'ask') return STEPS_ASK;
  const text = String(userText || '');
  if (/归因|敏感度|止损|止盈/.test(text)) return STEPS_ATTRIBUTE;
  if (/扫描|选股|机会/.test(text)) return STEPS_SCAN;
  if (/回测|重跑|再跑|均线|参数|改成|变成/.test(text)) return STEPS_BACKTEST;
  if (/创建|新建|写(一个)?策略|生成策略|建(一个)?策略/.test(text)) return STEPS_CREATE;
  return STEPS_DEFAULT;
}

function formatElapsed(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0));
  if (total < 15) return '';
  if (total < 60) return `已等待 ${total} 秒`;
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return rest ? `已等待 ${minutes} 分 ${rest} 秒` : `已等待 ${minutes} 分钟`;
}

/**
 * 进行中气泡：先走任务轨道，再轮换轻松文案，并显示等待时长。
 */
function PendingStream({ userText = '', kind = 'work', onTick }) {
  const steps = useMemo(() => resolvePendingSteps(userText, kind), [userText, kind]);
  const stepIntervalMs = kind === 'ask' ? 2400 : 4200;
  const holdIntervalMs = 5000;
  const [index, setIndex] = useState(0);
  const [holding, setHolding] = useState(false);
  const [holdIndex, setHoldIndex] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);
  const onTickRef = useRef(onTick);
  onTickRef.current = onTick;

  useEffect(() => {
    setIndex(0);
    setHolding(false);
    setHoldIndex(0);
    setElapsedSec(0);
  }, [userText, kind]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setElapsedSec((value) => value + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [userText, kind]);

  useEffect(() => {
    onTickRef.current?.();
  }, [index, holding, holdIndex]);

  useEffect(() => {
    if (holding) return undefined;
    if (index >= steps.length - 1) {
      const timer = window.setTimeout(() => {
        setHolding(true);
        setHoldIndex(0);
      }, stepIntervalMs);
      return () => window.clearTimeout(timer);
    }
    const timer = window.setTimeout(() => {
      setIndex((value) => Math.min(value + 1, steps.length - 1));
    }, stepIntervalMs);
    return () => window.clearTimeout(timer);
  }, [holding, index, stepIntervalMs, steps.length]);

  useEffect(() => {
    if (!holding) return undefined;
    const timer = window.setTimeout(() => {
      setHoldIndex((value) => (value + 1) % HOLDING_LINES.length);
    }, holdIntervalMs);
    return () => window.clearTimeout(timer);
  }, [holding, holdIndex, holdIntervalMs]);

  const label = holding
    ? HOLDING_LINES[holdIndex % HOLDING_LINES.length]
    : (steps[Math.min(index, steps.length - 1)] || STEPS_DEFAULT[0]);
  const elapsedLabel = formatElapsed(elapsedSec);

  return (
    <div className="ntq-assistant-dock__waiting" role="status" aria-live="polite">
      <LoadingBars barCount={4} className="ntq-loading-bars--sm" aria-label={label} />
      <div className="ntq-assistant-dock__waiting-copy">
        <span key={label} className="ntq-assistant-dock__waiting-text">
          {label}
        </span>
        {elapsedLabel ? (
          <span className="ntq-assistant-dock__waiting-elapsed">{elapsedLabel}</span>
        ) : null}
      </div>
    </div>
  );
}

PendingStream.propTypes = {
  userText: PropTypes.string,
  kind: PropTypes.oneOf(['ask', 'work']),
  onTick: PropTypes.func,
};

export default PendingStream;
