import React, { useEffect, useState } from 'react';
import { Box } from '@mui/material';
import { fetchMemberProfile, MEMBERSHIP_CHANGED_EVENT } from 'api/settingsApi';
import './style.scss';

const FALLBACK_REGISTER_URL = 'https://www.new-tea.cn/zh-hans/user/register';

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
    const onChanged = () => load();
    window.addEventListener(MEMBERSHIP_CHANGED_EVENT, onChanged);
    return () => {
      cancelled = true;
      window.removeEventListener(MEMBERSHIP_CHANGED_EVENT, onChanged);
    };
  }, []);

  const signedIn = Boolean(profile?.signed_in);
  const showAvatar = signedIn && profile.avatar && !avatarFailed;
  const registerUrl = profile?.register_url || FALLBACK_REGISTER_URL;
  const tierLabel = profile?.is_pro || profile?.tier === 'pro' ? 'Pro' : '标准';
  const catfoodText =
    profile?.catfood == null || Number.isNaN(Number(profile.catfood))
      ? null
      : Number(profile.catfood).toFixed(2);
  const chipTitle = [
    profile?.name,
    `${profile?.points ?? 0} 点数`,
    tierLabel,
    catfoodText != null ? `${catfoodText} 猫粮` : null,
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
          <Box component="span" className="ntq-member-strip__points">
            <Box component="span" className="ntq-member-strip__points-value">
              {tierLabel}
            </Box>
          </Box>
          {catfoodText != null ? (
            <Box component="span" className="ntq-member-strip__points">
              <Box component="span" className="ntq-member-strip__points-value">
                {catfoodText}
              </Box>
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
            <>
              <Box component="span" className="ntq-member-strip__hint">
                注册可以获得更多功能
              </Box>
              <Box
                component="a"
                className="ntq-member-strip__link"
                href={registerUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                去官网注册
              </Box>
            </>
          )}
        </Box>
      ) : null}
    </Box>
  );
}

export default MemberStrip;
