import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Heading, Message, Section } from 'ui';
import PageLayout from 'ntq-ui/pageLayout';
import WelcomeIntroCanvas from './welcomeIntroCanvas';
import { FALLBACK_DOCS_URL, fetchSiteUrls } from '../../api/siteApi';
import './welcomePage.scss';

const LOGO_SRC = '/logo.png';

const NEXT_LINKS = [
  {
    to: '/strategy-design',
    label: '制定策略',
    body: '您可以在这里看到当前所有本地的策略，也可以点击进入单个策略进行参数调试和回测。',
  },
  {
    to: '/scan',
    label: '策略选股',
    body: '您可以在这里使用自己调试完成的策略，扫描当前市场中的机会。',
  },
  {
    to: '/advanced/tags',
    label: '高级功能 → 特征标签',
    body: '您可以在这里对任何对象进行标签标记，以便在回测过程中快速分类或过滤数据，从而大大加快回测效率。',
  },
  {
    to: '/advanced/data-sources',
    label: '高级功能 → 数据源',
    body: '您可以在这里查看所有已经接入的外部数据源及其状态，并通过界面随时拉取和更新外部数据。',
  },
  {
    to: '/advanced/data-contracts',
    label: '高级功能 → 数据契约',
    body: '您可以在这里查看所有已经定义的可声明数据契约的信息和状态。',
  },
  {
    to: '/advanced/series-relation',
    label: '高级功能 → 序列关系',
    body: '您可以在这里对比任意两组或更多数据，从而从曲线中直观看出它们的关联和相关性。',
  },
  {
    to: '/advanced/post-process',
    label: '高级功能 → 后续处理',
    body: '您可以在这里定义：当市场通过策略扫描出机会时，后续如何处理它们。发邮件通知？再次过滤？喂给机器学习？都随您任意扩展。',
  },
  {
    to: '/settings/membership',
    label: '设置',
    body: '您可以在这里设置个人偏好和系统配置。',
  },
];

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
  const [docsUrl, setDocsUrl] = useState(FALLBACK_DOCS_URL);
  const [contactUrl, setContactUrl] = useState('');

  useEffect(() => {
    let alive = true;
    fetchSiteUrls()
      .then((urls) => {
        if (!alive) return;
        setDocsUrl(urls.docsUrl || FALLBACK_DOCS_URL);
        setContactUrl(urls.contactUrl || '');
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

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
      <div className="welcome-page__stack">
        <div className="welcome-hero">
          <img
            ref={logoRef}
            src={LOGO_SRC}
            alt="New Tea Quant"
            className="welcome-hero__logo"
          />
          <h1 className="welcome-hero__title">
            <span className="welcome-hero__en">Welcome</span>
            <span className="welcome-hero__sep" aria-hidden>|</span>
            <span className="welcome-hero__zh">欢迎使用</span>
          </h1>
        </div>

        <Section className="welcome-lower" gap="xl">
          <Message status="success">
            您的安装已经全部完成，欢迎使用新茶量化 (New Tea Quant)。
          </Message>

          <div>
            <Heading level="h2" gap="none">
              接下来：
            </Heading>
            <ul className="welcome-lower__list">
              <li>
                首先，您可以通过每个页面右上角悬浮的
                <strong>问号</strong>
                按钮打开当前页面帮助；也可以使用
                <strong>AI</strong>
                按钮打开 AI 新茶小助手，帮您完成任务。
              </li>
              {NEXT_LINKS.map((item) => (
                <li key={item.to}>
                  <RouterLink className="ntq-link" to={item.to}>
                    {item.label}
                  </RouterLink>
                  ：
                  {item.body}
                </li>
              ))}
              <li>
                <a
                  className="ntq-link"
                  href={docsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  文档
                </a>
                ：您可以在这里直接跳转到官网查看开发文档。
              </li>
              {contactUrl ? (
                <li>
                  <a
                    className="ntq-link"
                    href={contactUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    反馈
                  </a>
                  ：您可以在这里直接跳转到官网反馈问题或提出建议。NTQ 随时欢迎您的任何反馈和建议。
                </li>
              ) : null}
            </ul>
          </div>
        </Section>
      </div>

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
