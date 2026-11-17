# dialog

> 状态：**已实现** · 路径 `ui/message/dialog`

模态确认 / 说明弹层。MUI `Dialog` 仅作内部实现。

## 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `open` | `boolean` | `false` | 是否打开 |
| `onClose` | `(event, reason) => void` | — | 点遮罩 / Esc 时；忙碌中由调用方自行忽略 |
| `title` | `ReactNode` | `''` | 标题；空则不渲染标题区 |
| `children` | `ReactNode` | — | 正文 |
| `actions` | `ReactNode` | `null` | 底部操作（通常一组 `NtqButton`） |
| `size` | `'sm' \| 'md' \| 'lg'` | `'sm'` | 宽度档：窄确认 / 说明 / 较宽 |
| `disableEscapeKeyDown` | `boolean` | `false` | 禁止 Esc 关闭 |

## 用法

```js
import Dialog from 'ui/message/dialog';
import NtqButton from 'ui/button/button';

<Dialog
  open={open}
  onClose={() => !busy && setOpen(false)}
  title="确认清理缓存"
  size="sm"
  actions={(
    <>
      <NtqButton variant="ghost" onClick={() => setOpen(false)} disabled={busy}>取消</NtqButton>
      <NtqButton variant="danger" onClick={onConfirm} disabled={busy}>确认清理</NtqButton>
    </>
  )}
>
  <p className="ntq-muted">将清理所选缓存，此操作不可撤销。</p>
</Dialog>
```

危险确认用 `danger` 主按钮；一般确认用 `primary`。轻量瞬时反馈用 Toast / Message，不要用 Dialog。
