import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Icon from 'ui/icon/icon';
import './style.scss';

const DEFAULT_HOME = '/welcome';
const DEFAULT_LOGO = '/logo.png';
const DEFAULT_NAME = 'New Tea Quant';

/**
 * NTQ 品牌标：徽标 + 名称 + 可选 version 槽。
 *
 * @example
 * <AppBrand version={<AppVersion />} />
 * <AppBrand to="/welcome" linkComponent={DemoLink} />
 */
function AppBrand({
  to = DEFAULT_HOME,
  name = DEFAULT_NAME,
  logoSrc = DEFAULT_LOGO,
  version = null,
  linkComponent: Link = RouterLink,
  className = '',
  ...rest
}) {
  const [logoFailed, setLogoFailed] = useState(false);
  const rootClass = ['ntq-brand', className].filter(Boolean).join(' ');

  return (
    <Link
      to={to}
      className={rootClass}
      aria-label={`返回 ${name} 首页`}
      {...rest}
    >
      {logoFailed ? (
        <Icon name="tactic" size="xxl" className="ntq-brand__fallback-icon" />
      ) : (
        <img
          src={logoSrc}
          alt=""
          onError={() => setLogoFailed(true)}
          className="ntq-brand__logo"
        />
      )}
      <span className="ntq-brand__meta">
        <span className="ntq-brand__name">{name}</span>
        {version}
      </span>
    </Link>
  );
}

export default AppBrand;
