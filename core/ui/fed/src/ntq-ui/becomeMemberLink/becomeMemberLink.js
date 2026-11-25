import React from 'react';
import Button from 'ui/button/button';
import Icon from 'ui/icon/icon';
import { pickToken } from 'ui/tokens';
import './style.scss';

const VARIANTS = ['button', 'link'];

/**
 * 「成为会员」注册入口展示壳。
 * href 由应用层传入（fetchSiteUrls / profile.register_url），本组件不请求。
 *
 * @example
 * <BecomeMemberLink href={registerUrl} />
 * <BecomeMemberLink href={registerUrl} variant="link" />
 */
function BecomeMemberLink({
  href = '',
  label = '成为会员',
  variant = 'button',
  className = '',
  ...rest
}) {
  const url = String(href || '').trim();
  if (!url) return null;

  const variantToken = pickToken(variant, VARIANTS, 'button');

  if (variantToken === 'link') {
    return (
      <a
        className={['ntq-link', 'ntq-become-member-link', className].filter(Boolean).join(' ')}
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        {...rest}
      >
        <span>{label}</span>
        <Icon name="chevronRight" size="sm" />
      </a>
    );
  }

  return (
    <Button
      variant="glass"
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={['ntq-become-member-link', className].filter(Boolean).join(' ')}
      {...rest}
    >
      {label}
    </Button>
  );
}

export default BecomeMemberLink;
export { VARIANTS as BECOME_MEMBER_LINK_VARIANTS };
