import React, { useEffect, useState } from 'react';
import MemberStripView from 'ntq-ui/memberStrip';
import {
  fetchMemberProfile,
  fetchMembershipSettings,
  MEMBERSHIP_CHANGED_EVENT,
} from 'api/settingsApi';
import { FALLBACK_REGISTER_URL, resolveRegisterUrl } from 'api/siteApi';

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

/**
 * 顶栏会员条 container：拉 profile / 事件同步 → ntq-ui/memberStrip。
 */
function MemberStrip() {
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    let cancelled = false;
    let loadSeq = 0;
    let unreachableRetryId = 0;

    const load = () => {
      const seq = ++loadSeq;
      fetchMemberProfile()
        .then((next) => {
          if (cancelled || seq !== loadSeq) return;
          setProfile(next);
          if (!next?.signed_in && next?.reason === 'unreachable') {
            window.clearTimeout(unreachableRetryId);
            unreachableRetryId = window.setTimeout(() => {
              if (!cancelled) load();
            }, 2500);
          }
        })
        .catch(async () => {
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
      if (detailProfile && typeof detailProfile === 'object' && detailProfile.signed_in) {
        window.clearTimeout(unreachableRetryId);
        setProfile(detailProfile);
        return;
      }
      const nextCatfood = event?.detail?.catfood;
      const hasCatfood = nextCatfood != null && Number.isFinite(Number(nextCatfood));
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

  if (!profile) return null;

  const signedIn = Boolean(profile.signed_in);
  const isPro = Boolean(profile.is_pro || profile.tier === 'pro');
  const catfoodText =
    profile.catfood == null || Number.isNaN(Number(profile.catfood))
      ? null
      : Number(profile.catfood).toFixed(2);
  const freeText =
    profile.catfood_free == null || Number.isNaN(Number(profile.catfood_free))
      ? null
      : Number(profile.catfood_free).toFixed(2);
  const expiresAt = String(profile.catfood_free_expires_at || '').trim();
  const chipTitle = [
    profile.name,
    `${profile.points ?? 0} 点数`,
    isPro ? 'Pro' : '标准',
    catfoodText != null ? `还有 ${catfoodText} 猫粮` : null,
    freeText != null && Number(freeText) > 0 && expiresAt
      ? `其中 ${freeText} 在 ${expiresAt} 过期`
      : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <MemberStripView
      signedIn={signedIn}
      name={profile.name}
      avatar={profile.avatar || ''}
      isPro={isPro}
      points={profile.points}
      catfoodText={catfoodText}
      chipTitle={chipTitle}
      guestReason={signedIn ? '' : (profile.reason || 'missing')}
      registerUrl={resolveRegisterUrl(profile.register_url)}
    />
  );
}

export default MemberStrip;
