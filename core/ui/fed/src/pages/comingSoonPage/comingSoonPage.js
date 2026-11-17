import React from 'react';
import { Tag } from 'ui';
import PageLayout from 'ntq-ui/pageLayout';
import './style.scss';

/**
 * 导航中尚未实装的入口页：全宽由 AppShell 的 main 已套 ntq-content-inner
 */
function ComingSoonPage({ title, description }) {
  const desc = description || '该功能正在规划中，即将与桌面端工作流对接。';
  return (
    <PageLayout
      className="coming-soon-page"
      breadcrumbsItems={[{ label: '制定策略', to: '/strategy-design' }]}
      breadcrumbsCurrent={title}
      bannerTitle={title}
      bannerDescription={desc}
      bannerRightSlot={<Tag status="neutral" variant="outline">即将推出</Tag>}
    >
      <div className="coming-soon-page__card">
        <p className="coming-soon-page__note">
          敬请期待 - 我正在努力中...
        </p>
      </div>
    </PageLayout>
  );
}

export default ComingSoonPage;
