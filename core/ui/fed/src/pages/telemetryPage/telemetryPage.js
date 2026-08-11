import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Container,
  Link,
  Stack,
  Typography,
} from '@mui/material';
import './telemetryPage.scss';

function Section({ title, children }) {
  return (
    <Box className="telemetry-page__section">
      <Typography variant="h6" component="h2" className="telemetry-page__section-title">
        {title}
      </Typography>
      {children}
    </Box>
  );
}

function TelemetryPage() {
  return (
    <Box className="telemetry-page">
      <Container maxWidth="md" className="telemetry-page__inner">
        <Stack spacing={1} sx={{ mb: 3 }}>
          <Typography variant="h4" component="h1" fontWeight={700}>
            使用统计说明
          </Typography>
          <Typography variant="body1" color="text.secondary">
            New Tea Quant 可在征得你同意后，发送匿名使用数据以帮助改进产品。默认关闭；你可随时在设置中更改。
          </Typography>
          <Box sx={{ pt: 1 }}>
            <Button component={RouterLink} to="/settings/trace" variant="outlined" size="small">
              前往设置
            </Button>
          </Box>
        </Stack>

        <Section title="我们不会收集">
          <Typography variant="body2" color="text.secondary" component="div">
            <ul className="telemetry-page__list">
              <li>策略源码、参数原文或回测/扫描结果明细</li>
              <li>股票池内容、持仓、订单或交易记录</li>
              <li>姓名、邮箱、账号、IP 或其它可直接识别个人的信息</li>
              <li>本地文件路径中的用户名等敏感片段</li>
            </ul>
          </Typography>
        </Section>

        <Section title="每条事件附带的环境信息">
          <Typography variant="body2" color="text.secondary" paragraph>
            用于判断兼容性与资源画像，不含业务数据：
          </Typography>
          <Typography variant="body2" color="text.secondary" component="div">
            <ul className="telemetry-page__list">
              <li>匿名安装 ID（本机生成，与账号无关）</li>
              <li>操作系统、CPU 架构、Python 版本、NTQ 版本</li>
              <li>CPU 核心数、内存容量（MB）、磁盘类型、数据库类型</li>
            </ul>
          </Typography>
        </Section>

        <Section title="当前会上报的事件">
          <Typography variant="body2" color="text.secondary" paragraph>
            仅在你同意后发送；关闭同意后本地排队事件会被清空且不再上报。
          </Typography>
          <Typography variant="subtitle2" sx={{ mt: 1 }}>
            安装与启动
          </Typography>
          <Typography variant="body2" color="text.secondary" component="div">
            <ul className="telemetry-page__list">
              <li>
                <code>install.complete</code>
                ：安装是否成功、入口（UI / CLI）、稳定错误码（不含异常原文）
              </li>
              <li>
                <code>app.start</code>
                ：应用启动入口（UI / CLI / DevCLI）
              </li>
              <li>
                <code>track.decision</code>
                ：你开启或关闭使用统计时的选择来源
              </li>
            </ul>
          </Typography>

          <Typography variant="subtitle2" sx={{ mt: 2 }}>
            功能运行（
            <code>feature.run</code>
            ）
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            策略或标签跑完并写出性能报告后发送，用于了解耗时与规模，不含结果数据。
          </Typography>
          <Typography variant="body2" color="text.secondary" component="div">
            <ul className="telemetry-page__list">
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
                策略枚举额外：任务数、并行效率、时间分布（规划/读数/计算/报告等占比）、调度摘要
              </li>
              <li>价格因子 / 组合策略：上述公共字段</li>
              <li>标签运行：任务数及执行模式（如 entity / slice / global 等）</li>
            </ul>
          </Typography>
        </Section>

        <Section title="如何管理">
          <Typography variant="body2" color="text.secondary">
            打开
            {' '}
            <Link component={RouterLink} to="/settings/trace" underline="hover">
              设置 → 使用统计
            </Link>
            {' '}
            即可开启或关闭。删除本地同意记录后，下次启动会再次询问（全屏询问将在后续版本提供）。
          </Typography>
        </Section>
      </Container>
    </Box>
  );
}

export default TelemetryPage;
