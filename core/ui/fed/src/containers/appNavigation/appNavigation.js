import React from 'react';
import AppBrand from 'ntq-ui/appBrand';
import AppNav from 'ntq-ui/appNav';
import AppVersion from 'containers/appVersion';
import MemberStrip from 'containers/memberStrip';
import { useAppNavItems } from './useAppNavItems';
import './style.scss';

/**
 * 全局顶栏：品牌 + 导航 + 会员条。
 * 壳用语义 HTML；Brand / Nav 用 ntq-ui；会员条仍为业务 container。
 */
function AppNavigation() {
  const navItems = useAppNavItems();

  return (
    <header className="ntq-app-header">
      <div className="ntq-app-header__toolbar">
        <div className="ntq-content-inner ntq-app-header__band">
          <div className="ntq-app-header__inner">
            <AppBrand version={<AppVersion />} />
            <AppNav items={navItems} />
          </div>
          <MemberStrip />
        </div>
      </div>
    </header>
  );
}

export default AppNavigation;
