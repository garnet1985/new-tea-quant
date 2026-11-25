import React, { useCallback, useEffect, useState } from 'react';
import {
  Heading,
  Loading,
  Message,
  Button,
  Section,
  Tag,
  TextField as UiTextField,
} from 'ui';
import { BecomeMemberLink } from 'ntq-ui';
import { formatDateTime } from '../../../service/format/formatDateTime';
import {
  clearMembershipToken,
  fetchCatfoodLedger,
  fetchMemberMailQuota,
  fetchMemberProfile,
  fetchMembershipSettings,
  formatMailQuotaRemaining,
  notifyMembershipChanged,
  saveMembershipToken,
} from '../../../api/settingsApi';
import { fetchSiteUrls, resolveRegisterUrl } from '../../../api/siteApi';
import { useAsyncAction } from 'service/useAsyncAction';

const LEDGER_INITIAL = 20;
const LEDGER_MORE = 50;

function formatCatfoodSummary({ catfood, catfoodFree, catfoodPaid, catfoodFreeExpiresAt }) {
  if (catfood == null || !Number.isFinite(catfood)) return null;
  const total = Number(catfood).toFixed(2);
  const free = catfoodFree != null && Number.isFinite(catfoodFree) ? Number(catfoodFree) : null;
  const paid = catfoodPaid != null && Number.isFinite(catfoodPaid) ? Number(catfoodPaid) : null;
  const expire = catfoodFreeExpiresAt;

  if (free != null && free > 0 && expire) {
    return (
      <>
        您还有
        {' '}
        <strong className="settings-membership__em">{total}</strong>
        {' '}
        猫粮，其中
        {' '}
        <strong className="settings-membership__em">{free.toFixed(2)}</strong>
        {' '}
        （月赠）在
        {' '}
        {expire}
        {' '}
        过期
        {paid != null && paid > 0 ? (
          <>
            ；另有
            {' '}
            <strong className="settings-membership__em">{paid.toFixed(2)}</strong>
            {' '}
            充值余额不过期
          </>
        ) : null}
        。
      </>
    );
  }

  return (
    <>
      您还有
      {' '}
      <strong className="settings-membership__em">{total}</strong>
      {' '}
      猫粮
      {paid != null && paid > 0 ? '（充值余额不过期）' : ''}
      。
    </>
  );
}

export function SettingsMembershipPanel() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [saveOk, setSaveOk] = useState('');
  const [configured, setConfigured] = useState(false);
  const [invalid, setInvalid] = useState(false);
  const [token, setToken] = useState('');
  const [catfood, setCatfood] = useState(null);
  const [catfoodFree, setCatfoodFree] = useState(null);
  const [catfoodPaid, setCatfoodPaid] = useState(null);
  const [catfoodFreeExpiresAt, setCatfoodFreeExpiresAt] = useState(null);
  const [ledgerItems, setLedgerItems] = useState([]);
  const [ledgerLimit, setLedgerLimit] = useState(LEDGER_INITIAL);
  const [ledgerHasMore, setLedgerHasMore] = useState(false);
  const [ledgerLoading, setLedgerLoading] = useState(false);
  const [ledgerLoadingMore, setLedgerLoadingMore] = useState(false);
  const [mailQuota, setMailQuota] = useState(null);
  const [registerUrl, setRegisterUrl] = useState('');

  const saveAction = useAsyncAction(useCallback((value) => saveMembershipToken(value), []));
  const clearAction = useAsyncAction(useCallback(() => clearMembershipToken(), []));

  const applyState = useCallback((r) => {
    setConfigured(Boolean(r.configured));
    setInvalid(Boolean(r.invalid));
  }, []);

  const loadLedger = useCallback((ready, { limit = LEDGER_INITIAL, append = false } = {}) => {
    if (!ready) {
      setCatfood(null);
      setCatfoodFree(null);
      setCatfoodPaid(null);
      setCatfoodFreeExpiresAt(null);
      setLedgerItems([]);
      setLedgerLimit(LEDGER_INITIAL);
      setLedgerHasMore(false);
      setMailQuota(null);
      fetchMemberMailQuota()
        .then((q) => setMailQuota(q))
        .catch(() => setMailQuota(null));
      return;
    }
    const nextLimit = Math.max(1, Number(limit) || LEDGER_INITIAL);
    if (append) setLedgerLoadingMore(true);
    else setLedgerLoading(true);
    Promise.all([
      fetchMemberProfile().catch(() => null),
      fetchCatfoodLedger(nextLimit).catch(() => null),
      fetchMemberMailQuota().catch(() => null),
    ])
      .then(([profile, ledger, quota]) => {
        if (profile?.signed_in && profile.catfood != null) {
          setCatfood(Number(profile.catfood));
          setCatfoodFree(
            profile.catfood_free == null || Number.isNaN(Number(profile.catfood_free))
              ? null
              : Number(profile.catfood_free),
          );
          setCatfoodPaid(
            profile.catfood_paid == null || Number.isNaN(Number(profile.catfood_paid))
              ? null
              : Number(profile.catfood_paid),
          );
          setCatfoodFreeExpiresAt(String(profile.catfood_free_expires_at || '').trim() || null);
          // 设置页与顶栏各持一份 state：资料拉成功后推给顶栏，避免顶栏停在旧的 unreachable。
          notifyMembershipChanged({ profile });
        } else if (ledger?.available && ledger.catfood != null) {
          setCatfood(Number(ledger.catfood));
          setCatfoodFree(null);
          setCatfoodPaid(null);
          setCatfoodFreeExpiresAt(null);
          notifyMembershipChanged();
        } else {
          setCatfood(null);
          setCatfoodFree(null);
          setCatfoodPaid(null);
          setCatfoodFreeExpiresAt(null);
        }
        const items = Array.isArray(ledger?.items) ? ledger.items : [];
        setLedgerItems(items);
        setLedgerLimit(nextLimit);
        setLedgerHasMore(items.length >= nextLimit);
        setMailQuota(quota);
      })
      .finally(() => {
        setLedgerLoading(false);
        setLedgerLoadingMore(false);
      });
  }, []);

  const handleLedgerLoadMore = useCallback(() => {
    loadLedger(true, { limit: ledgerLimit + LEDGER_MORE, append: true });
  }, [ledgerLimit, loadLedger]);

  const load = useCallback(() => {
    setLoadError('');
    setLoading(true);
    Promise.all([
      fetchMembershipSettings(),
      fetchSiteUrls().catch(() => ({ registerUrl: '' })),
    ])
      .then(([r, urls]) => {
        applyState(r);
        setRegisterUrl(resolveRegisterUrl(urls.registerUrl));
        loadLedger(Boolean(r.configured));
      })
      .catch((e) => {
        setLoadError(e?.message || '读取会员凭证失败');
      })
      .finally(() => setLoading(false));
  }, [applyState, loadLedger]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async () => {
    setSaveOk('');
    saveAction.clearError();
    try {
      const r = await saveAction.run(token);
      applyState(r);
      setToken('');
      setSaveOk('通用凭证已装载。');
      loadLedger(Boolean(r.configured));
    } catch {
      /* saveAction.error */
    }
  };

  const handleClear = async () => {
    setSaveOk('');
    clearAction.clearError();
    try {
      const r = await clearAction.run();
      applyState(r);
      setToken('');
      setSaveOk('已移除通用凭证。');
      loadLedger(false);
    } catch {
      /* clearAction.error */
    }
  };

  if (loading) {
    return <Loading variant="inline" message="正在加载会员设置…" />;
  }

  const catfoodSummary = formatCatfoodSummary({
    catfood,
    catfoodFree,
    catfoodPaid,
    catfoodFreeExpiresAt,
  });

  return (
    <Section className="settings-membership" gap="lg">
      <Section className="settings-membership__token" gap="md">
        <div className="settings-membership__head">
          <Heading level="h3" gap="none">会员凭证设置</Heading>
          {!configured ? <BecomeMemberLink href={registerUrl} /> : null}
          <div className="settings-membership__status">
            <Tag
              status={configured ? 'success' : 'neutral'}
              variant={configured ? 'solid' : 'outline'}
            >
              {configured ? '已装载' : '尚未装载'}
            </Tag>
            {invalid ? (
              <p className="settings-membership__invalid">
                当前凭证无效，请重新粘贴并装载。
              </p>
            ) : null}
          </div>
        </div>
        <div className="ntq-muted">
          <p>
            请您在官网会员个人页找到会员通用凭证并粘贴到下方。
          </p>
          <ul>
            <li>装载后您可以使用新茶量化 AI 助手，并可以导入更多演示数据；</li>
            <li>如果没有会员凭证，仍可在「AI 配置」里用自己的 API Key 使用助手。</li>
          </ul>
          {!configured ? (
            <p>
              还没有账号时，先点「成为会员」注册，再到会员中心复制通用凭证回来装载。
            </p>
          ) : null}
        </div>
        {loadError ? <Message status="error">{loadError}</Message> : null}
        {saveOk ? <Message status="success">{saveOk}</Message> : null}
        {saveAction.error ? <Message status="error">{saveAction.error}</Message> : null}
        {clearAction.error ? <Message status="error">{clearAction.error}</Message> : null}
        <UiTextField
          label="通用凭证"
          placeholder="粘贴通用凭证"
          type="password"
          value={token}
          autoComplete="off"
          onChange={(e) => setToken(e.target.value)}
          hint="装载后本页不再显示已保存的凭证。"
        />
        <div className="settings-membership__actions">
          <Button
            variant="primary"
            disabled={saveAction.busy || !token.trim()}
            onClick={handleSave}
          >
            装载
          </Button>
          <Button
            variant="glass"
            disabled={clearAction.busy || (!configured && !invalid)}
            onClick={handleClear}
          >
            移除
          </Button>
        </div>
        <Message status="warning">
          请妥善保管您的通用凭证，请不要在非自己的电脑上装载，也不要随意暴露给他人。如果发现凭证泄漏，您可以马上登入官网刷新凭证并重新装载。
        </Message>
      </Section>

      <Section className="settings-membership__mail" gap="md">
        <Heading level="h3" gap="none">会员邮件额度</Heading>
        <p className="ntq-muted settings-membership__balance">
          {mailQuota?.policy
            || '目前共可发 30 封；只发到注册邮箱；每封邮件里最多显示 80 条机会'}
          。用于扫描后的邮件通知。
        </p>
        {configured ? (
          mailQuota?.available ? (
            <p className="ntq-muted">
              {formatMailQuotaRemaining(mailQuota) || '暂未读到剩余额度。'}
            </p>
          ) : (
            <p className="ntq-muted">
              {mailQuota?.reason === 'rejected'
                ? '凭证未被官网接受，暂时读不到剩余额度。'
                : '暂时读不到剩余额度，请稍后刷新。'}
            </p>
          )
        ) : (
          <p className="ntq-muted">装载会员凭证后可查看还可发几封。</p>
        )}
      </Section>

      {configured ? (
        <Section className="settings-membership__catfood" gap="md">
          <Heading level="h3" gap="none">猫粮</Heading>
          {catfoodSummary ? (
            <p className="ntq-muted settings-membership__balance">{catfoodSummary}</p>
          ) : (
            <p className="ntq-muted">暂未读到猫粮余额。</p>
          )}
          <div className="settings-membership__head">
            <Heading level="h4" gap="none">消耗记录</Heading>
            <Button
              variant="ghost"
              disabled={ledgerLoading || ledgerLoadingMore}
              onClick={() => loadLedger(true, { limit: LEDGER_INITIAL })}
            >
              刷新
            </Button>
          </div>
          <p className="ntq-muted">
            最近对话消耗、月赠与调整。默认最近
            {LEDGER_INITIAL}
            条。
          </p>
          {ledgerLoading ? <Loading variant="inline" /> : null}
          {!ledgerLoading && ledgerItems.length === 0 ? (
            <p className="ntq-muted">还没有记录。</p>
          ) : null}
          {!ledgerLoading && ledgerItems.length > 0 ? (
            <div className="settings-membership__ledger">
              {ledgerItems.map((row) => {
                const delta = Number(row.catfoodDelta);
                const deltaText = Number.isFinite(delta)
                  ? `${delta > 0 ? '+' : ''}${delta.toFixed(2)}`
                  : '—';
                const after = Number(row.catfoodBalanceAfter);
                const deltaTone = delta < 0 ? 'spend' : delta > 0 ? 'gain' : 'flat';
                return (
                  <div
                    key={row.id || `${row.created}-${row.reason}-${row.mode}`}
                    className="settings-membership__ledger-row"
                  >
                    <span className="settings-membership__ledger-time ntq-caption">
                      {formatDateTime(row.created, { style: 'absolute' })}
                    </span>
                    <span className="settings-membership__ledger-reason ntq-muted">
                      {row.reasonLabel || row.reason}
                    </span>
                    <span
                      className={[
                        'settings-membership__ledger-delta',
                        `settings-membership__ledger-delta--${deltaTone}`,
                      ].join(' ')}
                    >
                      {deltaText}
                    </span>
                    <span className="settings-membership__ledger-after ntq-caption">
                      {Number.isFinite(after) ? `→ ${after.toFixed(2)}` : ''}
                    </span>
                  </div>
                );
              })}
              {ledgerHasMore ? (
                <div className="settings-membership__ledger-more">
                  <Button
                    variant="ghost"
                    disabled={ledgerLoadingMore}
                    onClick={handleLedgerLoadMore}
                  >
                    {ledgerLoadingMore ? '加载中…' : `查看更多（后 ${LEDGER_MORE} 条记录）`}
                  </Button>
                </div>
              ) : null}
            </div>
          ) : null}
        </Section>
      ) : null}
    </Section>
  );
}

