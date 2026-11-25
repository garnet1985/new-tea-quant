import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Button } from 'ui';
import './whatWeWillTrackPage.scss';

function Section({ title, children }) {
  return (
    <section className="what-we-will-track-page__section">
      <h2 className="what-we-will-track-page__section-title">{title}</h2>
      {children}
    </section>
  );
}

function WhatWeWillTrackPage() {
  return (
    <div className="what-we-will-track-page">
      <div className="what-we-will-track-page__inner">
        <header className="what-we-will-track-page__intro">
          <h1 className="what-we-will-track-page__title">使用统计说明</h1>
          <p className="what-we-will-track-page__lead">
            New Tea Quant 可在征得你同意后，发送匿名使用数据以帮助改进产品。默认关闭；你可随时在设置中更改。
          </p>
          <div className="what-we-will-track-page__actions">
            <Button variant="glass" to="/settings/feedback" component={RouterLink}>
              前往设置
            </Button>
          </div>
        </header>

        <Section title="我们不会收集">
          <ul className="what-we-will-track-page__list">
            <li>策略源码、参数原文或回测/扫描结果明细</li>
            <li>股票池内容、持仓、订单或交易记录</li>
            <li>姓名、邮箱、账号、IP 或其它可直接识别个人的信息</li>
            <li>本地文件路径中的用户名等敏感片段</li>
          </ul>
        </Section>

        <Section title="每条事件附带的环境信息">
          <p className="what-we-will-track-page__copy">
            用于判断兼容性与资源画像，不含业务数据：
          </p>
          <ul className="what-we-will-track-page__list">
            <li>匿名安装 ID（本机生成，与账号无关）</li>
            <li>操作系统、CPU 架构、Python 版本、NTQ 版本</li>
            <li>CPU 核心数、内存容量（MB）、磁盘类型、数据库类型</li>
          </ul>
        </Section>

        <Section title="当前会上报的事件">
          <p className="what-we-will-track-page__copy">
            仅在你同意后发送；关闭同意后本地排队事件会被清空且不再上报。
          </p>
          <h3 className="what-we-will-track-page__subtitle">启动与同意</h3>
          <ul className="what-we-will-track-page__list">
            <li>
              <code>app.start</code>
              ：应用启动入口（UI / DevCLI；用户 CLI 仅策略/Tag 的 run 类命令，并带
              <code>command</code>
              原文）
            </li>
            <li>
              <code>track.decision</code>
              ：你开启或关闭使用统计时的选择来源
            </li>
          </ul>

          <h3 className="what-we-will-track-page__subtitle">
            功能运行（
            <code>feature.run</code>
            ）
          </h3>
          <p className="what-we-will-track-page__copy">
            策略或标签跑完并写出性能报告后发送，主要用于了解耗时与规模；组合/决策模拟会附带平均与最高资金利用率（不含盈亏金额）。
          </p>
          <ul className="what-we-will-track-page__list">
            <li>
              公共字段：
              <code>action</code>
              、
              <code>key</code>
              （策略/标签键名）、
              <code>mode</code>
              、
              <code>success</code>
              、
              <code>elapsed_seconds</code>
              、
              <code>entity_count</code>
            </li>
            <li>
              策略机会盘点额外：任务数、并行效率、时间分布（规划/读数/计算/报告等占比）、调度摘要
            </li>
            <li>价格因子：上述公共字段</li>
            <li>
              组合策略 / 决策模拟：公共字段，另含
              <code>capital_utilization_ratio_pct</code>
              （平均资金利用率）与
              <code>peak_capital_utilization_ratio_pct</code>
              （最高资金利用率）；决策模拟
              <code>action</code>
              为
              <code>strategy.decision</code>
            </li>
            <li>标签运行：任务数及执行模式（如 entity / slice / global 等）</li>
          </ul>
        </Section>

        <Section title="如何管理">
          <p className="what-we-will-track-page__copy">
            打开
            {' '}
            <RouterLink className="ntq-link" to="/settings/feedback">
              设置 → 反馈与统计
            </RouterLink>
            {' '}
            即可开启或关闭。删除本地同意记录后，下次进入应用会再次询问。
          </p>
        </Section>
      </div>
    </div>
  );
}

export default WhatWeWillTrackPage;
