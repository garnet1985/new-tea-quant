import React, { useCallback, useRef, useState } from 'react';
import { Box, Typography } from '@mui/material';
import PageLayout from '../../components/pageLayout/pageLayout';
import WelcomeIntroCanvas from './welcomeIntroCanvas';
import './welcomePage.scss';

const LOGO_SRC = '/logo.png';

function prefersReducedMotion() {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return false;
  }
}

function Path({ children }) {
  return <code className="welcome-path">{children}</code>;
}

function Term({ children }) {
  return <span className="welcome-term">{children}</span>;
}

function Mark({ children }) {
  return <mark className="welcome-mark">{children}</mark>;
}

function DocLink({ href, children }) {
  return (
    <a
      className="welcome-doc"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
    </a>
  );
}

function WelcomePage() {
  const logoRef = useRef(null);
  const skipIntro = prefersReducedMotion();
  const [introOn, setIntroOn] = useState(() => !skipIntro);
  const [pageReady, setPageReady] = useState(() => skipIntro);

  const pageClass = [
    'welcome-page',
    pageReady ? 'is-ready' : '',
    introOn ? 'is-intro-playing' : 'is-intro-done',
  ].filter(Boolean).join(' ');

  const revealPage = useCallback(() => {
    setPageReady(true);
  }, []);

  const finishIntro = useCallback(() => {
    setIntroOn(false);
    setPageReady(true);
  }, []);

  return (
    <PageLayout
      className={pageClass}
      showBreadcrumbs={false}
      showBanner={false}
    >
      <Box className="welcome-page__stack">
        <Box className="welcome-hero">
          <Box
            component="img"
            ref={logoRef}
            src={LOGO_SRC}
            alt="New Tea Quant"
            className="welcome-hero__logo"
          />
          <Typography className="welcome-hero__title" component="h1">
            <span className="welcome-hero__en">Welcome</span>
            <span className="welcome-hero__sep" aria-hidden>|</span>
            <span className="welcome-hero__zh">欢迎使用</span>
          </Typography>
        </Box>

        <Box className="welcome-lower">
          <Box className="welcome-lower__note">
            在您开始使用之前，强烈建议您先花 3 分钟阅读下边的简介，这会帮助您快速理解并上手
            <Term>NTQ</Term>
            。
          </Box>

          <Box className="welcome-lower__slot">
            <Typography className="welcome-lower__slot-title" component="h2">
              什么是 New Tea Quant（
              <Term>NTQ</Term>
              ）？
            </Typography>
            <Typography className="welcome-lower__lead" component="p">
              <Term>NTQ</Term>
              是一款回测与研究框架。本质上就做两件事：在您把交易准则抽象成代码能描述的规则后，
            </Typography>
            <ul className="welcome-lower__list">
              <li>在历史数据里验证规则是否可行</li>
              <li>使用您的规则在市场里寻找机会</li>
            </ul>
          </Box>

          <Box className="welcome-lower__slot">
            <Typography className="welcome-lower__slot-title" component="h2">
              我该从哪里做起？
            </Typography>
            <ul className="welcome-lower__list">
              <li>
                <strong>第一步：把您的想法变成规则。</strong>
                {' '}
                您需要明确地把脑海中的想法变成一个规则，比如我的超卖就是
                「
                <Mark>
                  <Term>RSI</Term>
                  {' < 20'}
                </Mark>
                」
                或是「我的热度是使用近期波动和成交量衡量的，当它们都在某个范围内就视作机会」。
              </li>
              <li>
                <strong>第二步：把想法变成代码。</strong>
                {' '}
                您需要在
                <Path>userspace/strategies</Path>
                给您的策略建立一个目录，里边需要 2 个文件，分别是
                <Path>strategy.py</Path>
                和
                <Path>settings.py</Path>
                。您可以通过拷贝演示策略，或拷贝
                <Path>_template</Path>
                目录再重命名的方式来创建。
                {' '}
                在您的
                <Path>strategy.py</Path>
                中，您需要实现
                <Path>has_opportunity</Path>
                方法，这个方法就是您抽象出的量化规则：返回
                <Path>True</Path>
                代表当前股票当前时间点有机会，
                <Path>False</Path>
                则反之。
                {' '}
                您还需要在
                <Path>settings.py</Path>
                中定义一些参数，比如您的回测需要什么数据、什么指标、起点、终点等等。当然还要定义一个明确的交易目标。
                {' '}
                更多的帮助可以参考
                <DocLink href="https://new-tea.cn/zh-hans/using-strategy-example">这篇文档</DocLink>
                。
              </li>
              <li>
                <strong>第三步：在历史数据中验证想法。</strong>
                {' '}
                完成代码编写和配置后，您就可以在
                <Term>UI</Term>
                上进行调试了。您可以把核心参数放入
                <Path>settings.py</Path>
                的
                <Path>core</Path>
                中，比如
                <Term>RSI</Term>
                的阈值、热度的范围等等。这样
                <Term>UI</Term>
                上会显示出这些数值，您只要修改并运行就能看到阈值变化对结果的影响。
                {' '}
                每个步骤完成时会有一份详尽的报告，告诉您当前想法把握机会的能力、抓住价格波动的能力，以及实盘模拟，并且对您的参数进行归因。调试到您觉得合理的区间后，就可以使用这个策略了。
              </li>
              <li>
                <strong>第四步：在最新市场里寻找机会。</strong>
                {' '}
                您可以在
                <Term>UI</Term>
                的
                <Term>策略选股</Term>
                里看到您所有的策略，然后使用它们去扫描最新市场，找到符合您策略的机会并报告给您。
                {' '}
                <Mark>但请注意，这需要您接入自己的数据源才行。</Mark>
                更多的信息可以参考
                <DocLink href="https://new-tea.cn/zh-hans/using-strategy-to-find-opportunities">这篇文档</DocLink>
                。
              </li>
            </ul>
          </Box>

          <Box className="welcome-lower__slot">
            <Typography className="welcome-lower__slot-title" component="h2">
              其他的页面都是做什么的？
            </Typography>
            <ul className="welcome-lower__list">
              <li>
                <strong>
                  <Term>特征标签</Term>
                </strong>
                {' '}
                这个页面用来查看您对各种数据和股票做的特征标记。特征标签是可重用的预处理标记，比如您想对一只股票所有的记录进行市值分类，或标记一个公司是不是高负债率，这样在回测中可以直接通过
                <Path>settings.py</Path>
                的配置注入这些标签并使用。
                {' '}
                标签的用法类似策略：您需要抽象出标签的准则，然后在
                <Path>userspace/extensions/tags</Path>
                目录下创建
                <Path>tag.py</Path>
                和
                <Path>settings.py</Path>
                ，再像运行策略一样单独运行。
                {' '}
                标签的
                <Term>UI</Term>
                只能告诉您这个标签是不是最新的、它是什么类型，以及快捷开始按钮。
                {' '}
                如果您想了解更多关于 tag 的用法，请参考
                <DocLink href="https://new-tea.cn/zh-hans/using-tag-example">这篇文档</DocLink>
                。
              </li>
              <li>
                <strong>
                  <Term>数据源</Term>
                </strong>
                {' '}
                <Term>NTQ</Term>
                自带了一套数据源（如果您在安装的时候导入过），您可以在
                <Term>UI</Term>
                里查看它们，并且可以让它们开始获取最新数据。
                {' '}
                <Mark>但请注意，NTQ 不自带持续的数据源。</Mark>
                如果您需要不停更新数据（尤其是扫描机会需要使用），您需要自己接入自己的数据源。
                {' '}
                您可以通过
                <DocLink href="https://new-tea.cn/zh-hans/using-datasource-example">这篇文档</DocLink>
                了解更多。
              </li>
              <li>
                <strong>
                  <Term>数据契约</Term>
                </strong>
                {' '}
                数据契约是让一组数据绑定在一个独一无二的
                <Path>data_key</Path>
                上，这样您在制定策略时就可以在
                <Path>settings.py</Path>
                里直接声明这个 key，数据就会自动注入回测流程。
                {' '}
                <Term>UI</Term>
                用来帮您看清不同契约的名字、描述和 key，方便在代码中使用。
                {' '}
                您可以通过
                <DocLink href="https://new-tea.cn/zh-hans/using-data-contract-example">这篇文档</DocLink>
                了解更多。
              </li>
            </ul>
          </Box>
        </Box>
      </Box>

      {introOn ? (
        <WelcomeIntroCanvas
          logoRef={logoRef}
          onPageReveal={revealPage}
          onDone={finishIntro}
        />
      ) : null}
    </PageLayout>
  );
}

export default WelcomePage;
