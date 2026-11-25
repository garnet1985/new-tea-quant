import React from 'react';
import Message from 'ui/message/message';
import './style.scss';

/**
 * 策略演示风险提示：负收益解读 + 免责声明。
 * 策略列表 / 制定工作台 / 扫描列表共用。
 */
export default function StrategyDisclaimer({ className = '' }) {
  return (
    <Message
      status="warning"
      className={['ntq-strategy-disclaimer', className].filter(Boolean).join(' ')}
    >
      <p className="ntq-strategy-disclaimer__title">演示策略仅供学习与功能演示，不构成任何投资建议，请勿将其直接用于实盘交易。</p>
    </Message>
  );
}
