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
          <Box className="welcome-lower__slot">
            <Typography className="welcome-lower__slot-title" component="h2">
              在您开始使用之前，强烈地建议您先花3分钟阅读下边的简介，这会帮助您快速理解并上手NTQ。
            </Typography>
          </Box>
        
          <Box className="welcome-lower__slot">
            <Typography className="welcome-lower__slot-title" component="h2">
              什么是 New Tea Quant（NTQ）？
            </Typography>
            <Typography className="welcome-lower__lead" component="p">
              NTQ是一款面向个人开发者的轻量、高性能量化回测与研究框架。本质上就做两件事：在您把您的交易准则抽象成一个代码能描述的规则后，
            </Typography>
            <ul className="welcome-lower__list">
              <li>在历史数据里验证您的交易准则是否可行</li>
              <li>使用您交易准则在最新市场里寻找机会并报告给您</li>
            </ul>
          </Box>

          <Box className="welcome-lower__slot">
            <Typography className="welcome-lower__slot-title" component="h2">
              我该从哪里做起？
            </Typography>
            <ul className="welcome-lower__list">
              <li>
                <strong>第一步：把您的想法变成代码。</strong>
                {' '}
                您需要您明确地把脑海中的想法变成一个准则，比如我的超卖就是"RSI &lt; 20" 或是 "我的热度是使用近期波动和成交量衡量的，当他们都在某个范围内就视作机会"。
              </li>
              <li>
                <strong>第二步：把想法变成代码。</strong>
                {' '}
                您需要在userspace中的strategies给您的策略建立一个目录，里边需要2个文件，分别是strategy.py和settings.py，您可以通过拷贝演示策略或者_template目录再重命名的方式来创建。
                {' '}
                在您的strategy.py中，您需要实现has_opportunity的方法，这个方法就是您抽象出的量化规则，它返回True代表当前股票当前时间点有机会，False则反之。
                {' '}
                您还需要在settings.py中定义一些参数，比如您的回测需要什么数据，什么指标，起点，终点，等等。当然还要定义一个明确的交易目标。
              </li>
              <li>
                <strong>第三步：在历史数据中验证想法。</strong>
                {' '}
                完成代码编写和设置配置后您就可以在UI上进行调试了，您可以把核心参数放入settings文件的core中。比如RSI的阈值，热度的范围，等等。这样，UI上会显示出您的这些数值，您只要修改并运行就能看到阈值变化对于结果的影响。
                {' '}
                在每个步骤完成的时候会有一份详尽的报告告诉您当前想法把握机会的能力，抓住价格波动的能力和实盘的模拟，并且对您的参数进行归因。在您调试到您觉得合理的区间后，您就可以使用这个策略了。
              </li>
              <li>
                <strong>第四步：在最新市场里寻找机会。</strong>
                {' '}
                您可以在UI的策略选股里看到您所有的策略，然后使用他们去扫描最新市场，找到符合您策略的机会并报告给您。
                {' '}
                但请注意，这需要您接入自己的数据源才行。
              </li>
            </ul>
          </Box>
          <Box className="welcome-lower__slot">
            <Typography className="welcome-lower__slot-title" component="h2">
              其他的页面都是做什么的？
            </Typography>
            <ul className="welcome-lower__list">
              <li>
                <strong>特征标签页</strong>
                {' '}
                这个页面是用来看到您对各种数据和股票的特征进行标记的页面。特征标签是一个可重用的预处理标记，比如您想对一只股票所有的记录进行市值分类，或者您想标记一个公司是不是高负债率等等，这样您在回测中可以直接通过settings的配置注入这些标签并且直接使用。
                {' '}
                标签的用法类似策略，您需要抽象出标签的准则，然后在userspace/extensions/tags目录下创建tags.py，和settings.py， 然后需要像运行策略一样单独运行。
                {' '}
                标签的UI只能告诉您这个标签是不是最新的，它是什么类型的，和快捷开始按钮。
              </li>
              <li>
                <strong>数据源页面</strong>
                {' '}
                NTQ自带了一套数据源（如果您在安装的时候导入过），您可以在UI里查看他们，并且可以让他们开始获取最新数据。
                {' '}
                但是请注意，NTQ不自带持续的数据源，如果您需要不停更新数据（尤其是扫描机会需要使用），您需要自己接入自己的数据源。
              </li>
              <li>
                <strong>数据契约页面</strong>
                {' '}
                数据契约是让一组数据绑定在一个独一无二的key上，这样您就可以在制定策略的时候在settings里直接声明这个data key，这样数据就可以自动注入回测的流程当中了。
                {' '}
                UI的页面是辅助您清晰的看到不同契约的名字，描述和key，这样可以方便您在代码中使用。
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
