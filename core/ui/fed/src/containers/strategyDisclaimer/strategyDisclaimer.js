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
      <p className="ntq-strategy-disclaimer__title">使用提示</p>
      <ul className="ntq-strategy-disclaimer__list">
        <li>
          回测收益为负时，未必说明策略思路或算法本身有问题。常见原因还包括：回测区间内市场整体偏弱、
          止损/止盈参数设置不当、股票池筛选不合理，以及仓位与资金管理约束等。建议结合市场环境与参数一并复盘。
        </li>
        <li>
          本产品中的演示策略仅供学习与功能演示，不构成任何投资建议。请勿将其直接用于实盘交易；
          因直接使用演示策略造成的损失，我们不承担任何责任。
        </li>
      </ul>
    </Message>
  );
}
