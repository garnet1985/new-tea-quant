import React, { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box } from '@mui/material';
import {
  fetchMemberProfile,
  fetchMembershipSettings,
  MEMBERSHIP_CHANGED_EVENT,
} from 'api/settingsApi';
import { FALLBACK_REGISTER_URL, resolveRegisterUrl } from 'api/siteApi';
import './style.scss';

function letterOf(name) {
  const text = String(name || '').trim();
  if (!text) return '?';
  return text.slice(0, 1).toUpperCase();
}

function guestProfile(reason = 'missing') {
  return {
    signed_in: false,
    register_url: FALLBACK_REGISTER_URL,
    name: '',
    avatar: '',
    points: null,
    tier: null,
    is_pro: false,
    catfood: null,
    reason,
  };
}

function MemberStrip() {
  const [profile, setProfile] = useState(null);
  const [avatarFailed, setAvatarFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let loadSeq = 0;
    let unreachableRetryId = 0;

    const load = () => {
      const seq = ++loadSeq;
      fetchMemberProfile()
        .then((next) => {
          if (cancelled || seq !== loadSeq) return;
          setAvatarFailed(false);
          setProfile(next);
          // 启动瞬间偶发失败时短延迟再拉一次。
          if (!next?.signed_in && next?.reason === 'unreachable') {
            window.clearTimeout(unreachableRetryId);
            unreachableRetryId = window.setTimeout(() => {
              if (!cancelled) load();
            }, 2500);
          }
        })
        .catch(async () => {
          // 缺凭证不是断网；仅「已装载凭证却读不到官网」才标 unreachable。
          let reason = 'missing';
          try {
            const membership = await fetchMembershipSettings();
            if (membership?.configured) reason = 'unreachable';
          } catch (_err) {
            reason = 'missing';
          }
          if (cancelled || seq !== loadSeq) return;
          setProfile(guestProfile(reason));
          if (reason === 'unreachable') {
            window.clearTimeout(unreachableRetryId);
            unreachableRetryId = window.setTimeout(() => {
              if (!cancelled) load();
            }, 2500);
          }
        });
    };

    load();
    const onChanged = (event) => {
      const detailProfile = event?.detail?.profile;
      // 设置页已拉到的资料直接同步到顶栏（两边原先各自一份 state）。
      if (detailProfile && typeof detailProfile === 'object' && detailProfile.signed_in) {
        window.clearTimeout(unreachableRetryId);
        setAvatarFailed(false);
        setProfile(detailProfile);
        return;
      }
      const nextCatfood = event?.detail?.catfood;
      const hasCatfood = nextCatfood != null && Number.isFinite(Number(nextCatfood));
      // 已登录时先乐观更新猫粮；未登录时必须整表重拉，不能直接 return。
      if (hasCatfood) {
        let updatedSignedIn = false;
        setProfile((prev) => {
          if (!prev?.signed_in) return prev;
          updatedSignedIn = true;
          return { ...prev, catfood: Number(Number(nextCatfood).toFixed(2)) };
        });
        if (updatedSignedIn) return;
      }
      load();
    };
    const onVisible = () => {
      if (document.visibilityState === 'visible') load();
    };
    window.addEventListener(MEMBERSHIP_CHANGED_EVENT, onChanged);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      cancelled = true;
      window.clearTimeout(unreachableRetryId);
      window.removeEventListener(MEMBERSHIP_CHANGED_EVENT, onChanged);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, []);

  const signedIn = Boolean(profile?.signed_in);
  const showAvatar = signedIn && profile.avatar && !avatarFailed;
  const registerUrl = resolveRegisterUrl(profile?.register_url);
  const isPro = Boolean(profile?.is_pro || profile?.tier === 'pro');
  const catfoodText =
    profile?.catfood == null || Number.isNaN(Number(profile.catfood))
      ? null
      : Number(profile.catfood).toFixed(2);
  const freeText =
    profile?.catfood_free == null || Number.isNaN(Number(profile.catfood_free))
      ? null
      : Number(profile.catfood_free).toFixed(2);
  const expiresAt = String(profile?.catfood_free_expires_at || '').trim();
  const chipTitle = [
    profile?.name,
    `${profile?.points ?? 0} 点数`,
    isPro ? 'Pro' : '标准',
    catfoodText != null ? `还有 ${catfoodText} 猫粮` : null,
    freeText != null && Number(freeText) > 0 && expiresAt
      ? `其中 ${freeText} 在 ${expiresAt} 过期`
      : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <Box className="ntq-member-strip">
      {signedIn ? (
        <Box className="ntq-member-strip__chip" title={chipTitle}>
          {showAvatar ? (
            <Box
              component="img"
              className="ntq-member-strip__avatar"
              src={profile.avatar}
              alt=""
              onError={() => setAvatarFailed(true)}
            />
          ) : (
            <Box className="ntq-member-strip__letter" aria-hidden="true">
              {letterOf(profile.name)}
            </Box>
          )}
          <Box component="span" className="ntq-member-strip__name">
            {profile.name}
          </Box>
          {isPro ? (
            <Box component="span" className="ntq-member-strip__pro" aria-label="Pro">
              Pro
            </Box>
          ) : null}
          {catfoodText != null ? (
            <Box
              component={RouterLink}
              to="/settings/membership"
              className="ntq-member-strip__points ntq-member-strip__points--link"
              title="查看猫粮明细"
            >
              还有
              {' '}
              <Box component="span" className="ntq-member-strip__points-value">
                {catfoodText}
              </Box>
              {' '}
              猫粮
            </Box>
          ) : (
            <Box component="span" className="ntq-member-strip__points">
              <Box component="span" className="ntq-member-strip__points-value">
                {profile.points}
              </Box>
              点数
            </Box>
          )}
        </Box>
      ) : profile ? (
        <Box className="ntq-member-strip__chip">
          {profile.reason === 'unreachable' ? (
            <Box component="span" className="ntq-member-strip__hint">
              暂时连不上官网
            </Box>
          ) : profile.reason === 'rejected' ? (
            <Box component="span" className="ntq-member-strip__hint">
              凭证无效，请到设置重新装载
            </Box>
          ) : (
            <Box component="span" className="ntq-member-strip__hint">
              注册可以获得更多功能
            </Box>
          )}
          {profile.reason === 'unreachable' || profile.reason === 'rejected' ? (
            <Box
              component={RouterLink}
              className="ntq-member-strip__link"
              to="/settings/membership"
            >
              会员设置
            </Box>
          ) : (
            <Box
              component="a"
              className="ntq-member-strip__link"
              href={registerUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              成为会员
            </Box>
          )}
        </Box>
      ) : null}
    </Box>
  );
}

export default MemberStrip;
