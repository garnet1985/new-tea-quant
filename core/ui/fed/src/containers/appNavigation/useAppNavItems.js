import { useEffect, useMemo, useState } from 'react';
import { fetchSiteUrls } from 'api/siteApi';

/** 产品顶栏路由表（应用层；不进 ntq-ui）。 */
const STATIC_NAV_ITEMS = [
  { label: '制定策略', to: '/strategy-design', icon: 'tactic' },
  { label: '策略选股', to: '/scan', icon: 'monitoring' },
  {
    label: '高级功能',
    icon: 'dataObject',
    match: '/advanced',
    children: [
      { label: '特征标签', to: '/advanced/tags' },
      { label: '数据源', to: '/advanced/data-sources' },
      { label: '数据契约', to: '/advanced/data-contracts' },
      { label: '序列关系', to: '/advanced/series-relation' },
      { label: '后续处理', to: '/advanced/post-process' },
    ],
  },
];

const SETTINGS_ITEM = {
  label: '设置',
  to: '/settings/membership',
  icon: 'settings',
  match: '/settings',
};

/**
 * 组装顶栏 AppNav items：静态路由 + 站点文档/反馈外链（fetchSiteUrls）。
 */
export function useAppNavItems() {
  const [docsUrl, setDocsUrl] = useState('');
  const [contactUrl, setContactUrl] = useState('');

  useEffect(() => {
    let alive = true;
    fetchSiteUrls()
      .then((urls) => {
        if (!alive) return;
        setDocsUrl(urls.docsUrl || '');
        setContactUrl(urls.contactUrl || '');
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  return useMemo(() => {
    const items = [...STATIC_NAV_ITEMS];
    if (docsUrl) {
      items.push({ label: '文档', href: docsUrl, icon: 'help' });
    }
    if (contactUrl) {
      items.push({ label: '反馈', href: contactUrl, icon: 'chat' });
    }
    items.push(SETTINGS_ITEM);
    return items;
  }, [docsUrl, contactUrl]);
}

export default useAppNavItems;
