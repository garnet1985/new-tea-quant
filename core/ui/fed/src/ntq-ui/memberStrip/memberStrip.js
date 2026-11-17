import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Avatar from 'ui/avatar/avatar';
import ProBadge from 'ntq-ui/proBadge';
import './style.scss';

/**
 * 顶栏会员条展示壳（挂角 chip）。
 * 资料拉取留在 containers/memberStrip。
 *
 * @example
 * <MemberStrip
 *   signedIn
 *   name="茶"
 *   isPro
 *   catfoodText="12.50"
 *   membershipTo="/settings/membership"
 * />
 */
function MemberStrip({
  signedIn = false,
  name = '',
  avatar = '',
  isPro = false,
  points = null,
  catfoodText = null,
  chipTitle = '',
  guestReason = '',
  registerUrl = '',
  membershipTo = '/settings/membership',
  linkComponent: Link = RouterLink,
  className = '',
  ...rest
}) {
  const rootClass = ['ntq-member-strip', className].filter(Boolean).join(' ');

  if (signedIn) {
    return (
      <div className={rootClass} {...rest}>
        <div className="ntq-member-strip__chip" title={chipTitle || undefined}>
          <Avatar
            className="ntq-member-strip__avatar"
            src={avatar || undefined}
            name={name}
            size="sm"
            alt=""
          />
          <span className="ntq-member-strip__name">{name}</span>
          {isPro ? <ProBadge /> : null}
          {catfoodText != null ? (
            <Link
              to={membershipTo}
              className="ntq-member-strip__points ntq-member-strip__points--link"
              title="查看猫粮明细"
            >
              还有
              {' '}
              <span className="ntq-member-strip__points-value">{catfoodText}</span>
              {' '}
              猫粮
            </Link>
          ) : (
            <span className="ntq-member-strip__points">
              <span className="ntq-member-strip__points-value">{points}</span>
              点数
            </span>
          )}
        </div>
      </div>
    );
  }

  if (!guestReason && !registerUrl) {
    return null;
  }

  const hint = guestReason === 'unreachable'
    ? '暂时连不上官网'
    : guestReason === 'rejected'
      ? '凭证无效，请到设置重新装载'
      : '注册可以获得更多功能';

  const showSettingsLink = guestReason === 'unreachable' || guestReason === 'rejected';

  return (
    <div className={rootClass} {...rest}>
      <div className="ntq-member-strip__chip">
        <span className="ntq-member-strip__hint">{hint}</span>
        {showSettingsLink ? (
          <Link className="ntq-member-strip__link" to={membershipTo}>
            会员设置
          </Link>
        ) : (
          <a
            className="ntq-member-strip__link"
            href={registerUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            成为会员
          </a>
        )}
      </div>
    </div>
  );
}

export default MemberStrip;
