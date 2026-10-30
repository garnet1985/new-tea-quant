import React, { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box } from '@mui/material';
import { fetchMemberProfile, MEMBERSHIP_CHANGED_EVENT } from 'api/settingsApi';
import { FALLBACK_REGISTER_URL, resolveRegisterUrl } from 'api/siteApi';
import './style.scss';

function letterOf(name) {
  const text = String(name || '').trim();
  if (!text) return '?';
  return text.slice(0, 1).toUpperCase();
}

function MemberStrip() {
  const [profile, setProfile] = useState(null);
  const [avatarFailed, setAvatarFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const load = () => {
      fetchMemberProfile()
        .then((next) => {
          if (!cancelled) {
            setAvatarFailed(false);
            setProfile(next);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setProfile({
              signed_in: false,
              register_url: FALLBACK_REGISTER_URL,
              name: '',
              avatar: '',
              points: null,
              tier: null,
              is_pro: false,
              catfood: null,
              reason: 'unreachable',
            });
          }
        });
    };

    load();
    const onChanged = (event) => {
      const nextCatfood = event?.detail?.catfood;
      if (nextCatfood != null && Number.isFinite(Number(nextCatfood))) {
        setProfile((prev) => (
          prev?.signed_in
            ? { ...prev, catfood: Number(Number(nextCatfood).toFixed(2)) }
            : prev
        ));
        return;
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
          ) : (
            <Box component="span" className="ntq-member-strip__hint">
              注册可以获得更多功能
            </Box>
          )}
          <Box
            component="a"
            className="ntq-member-strip__link"
            href={registerUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            成为会员
          </Box>
        </Box>
      ) : null}
    </Box>
  );
}

export default MemberStrip;
