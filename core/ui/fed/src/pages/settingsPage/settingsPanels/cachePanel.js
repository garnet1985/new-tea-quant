import React, { useMemo, useState } from 'react';
import {
  Checkbox as UiCheckbox,
  Dialog,
  Heading,
  Message,
  Button,
  Section,
  Tag,
} from 'ui';
import {
  clearSettingsCache,
} from '../../../api/settingsApi';

const CACHE_OPTIONS = [
  {
    key: 'clear_backtest_results',
    label: '回测结果临时文件清理',
    hint: '删除各策略 results/simulations/ 下的机会盘点、价格、投资模拟产物。',
  },
  {
    key: 'clear_scan_results',
    label: '扫描结果临时文件清理',
    hint: '删除各策略 results/scan/ 下的扫描机会缓存。',
  },
  {
    key: 'clear_userspace_ntq',
    label: '用户空间缓存清理',
    hint: '删除 userspace/.ntq/（进度、pipeline 租约、tmp 等）。不含仓库根 .ntq/。勾选此项时已包含下方静态数据包。',
  },
  {
    key: 'clear_static_packages',
    label: '静态数据包清理',
    hint: '删除 userspace/.ntq/packages/ 下已下载的 demo / member / full 数据包。下次导入需重新下载。',
  },
];

const DEFAULT_CACHE_SELECTION = {
  clear_backtest_results: true,
  clear_scan_results: true,
  clear_userspace_ntq: true,
  clear_static_packages: false,
};

export function SettingsCachePanel() {
  const [selection, setSelection] = useState({ ...DEFAULT_CACHE_SELECTION });
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [clearError, setClearError] = useState('');
  const [clearOk, setClearOk] = useState('');

  const hasSelection = useMemo(
    () => Object.values(selection).some(Boolean),
    [selection],
  );

  const selectedLabels = useMemo(
    () => CACHE_OPTIONS.filter((opt) => selection[opt.key]).map((opt) => opt.label),
    [selection],
  );

  const handleToggle = (key) => (_event, checked) => {
    setSelection((prev) => ({ ...prev, [key]: checked }));
    setClearOk('');
    setClearError('');
  };

  const handleConfirmClear = () => {
    setClearing(true);
    setClearError('');
    setClearOk('');
    clearSettingsCache(selection)
      .then((res) => {
        setClearOk(res.message || '缓存已经全部清理');
        setSelection({ ...DEFAULT_CACHE_SELECTION });
      })
      .catch((e) => {
        setClearError(e?.message || '清理失败');
      })
      .finally(() => {
        setClearing(false);
        setConfirmOpen(false);
      });
  };

  return (
    <Section className="settings-cache" gap="lg">
      <Section className="settings-cache__types" gap="md">
        <Heading level="h3" gap="none">缓存管理</Heading>
        <p className="ntq-muted">
          勾选需要清理的缓存类型，点击「一键清理」。有 Tag、扫描、回测等任务进行中时将拒绝清理。
        </p>
        {clearError ? <Message status="error">{clearError}</Message> : null}
        {clearOk ? <Message status="success">{clearOk}</Message> : null}
        <div className="settings-cache__options" role="group" aria-label="缓存清理选项">
          {CACHE_OPTIONS.map((opt) => (
            <UiCheckbox
              key={opt.key}
              className="settings-cache__option"
              checked={Boolean(selection[opt.key])}
              onChange={handleToggle(opt.key)}
              disabled={clearing}
              label={(
                <span className="settings-cache__option-text">
                  <span className="settings-cache__option-title">{opt.label}</span>
                  <span className="settings-cache__option-hint">{opt.hint}</span>
                </span>
              )}
            />
          ))}
        </div>
      </Section>

      <Section className="settings-cache__form-actions" gap="md">
        <div className="settings-cache__actions">
          <Button
            variant="danger"
            disabled={!hasSelection || clearing}
            onClick={() => setConfirmOpen(true)}
          >
            {clearing ? '清理中…' : '一键清理'}
          </Button>
        </div>
        <Dialog
          open={confirmOpen}
          onClose={() => !clearing && setConfirmOpen(false)}
          title="确认清理缓存"
          size="sm"
          actions={(
            <>
              <Button
                variant="ghost"
                onClick={() => setConfirmOpen(false)}
                disabled={clearing}
              >
                取消
              </Button>
              <Button
                variant="danger"
                onClick={handleConfirmClear}
                disabled={clearing}
              >
                {clearing ? '清理中…' : '确认清理'}
              </Button>
            </>
          )}
        >
          <div className="settings-cache__dialog-body">
            <p className="ntq-muted">将清理以下项，此操作不可撤销：</p>
            <ul className="settings-cache__dialog-list">
              {selectedLabels.map((label) => (
                <li key={label}>{label}</li>
              ))}
            </ul>
          </div>
        </Dialog>
      </Section>
    </Section>
  );
}
