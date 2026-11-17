# toast

右下角短暂弹出。宿主 + 总线；内容复用 `Message`（状态模式）。

```js
import ToastHost, { showToast } from 'ui/message/toast';

<ToastHost />

showToast({ status: 'success', content: '已保存' });
showToast({ status: 'error', content: '网络异常', duration: 4000 });
showToast({ status: 'info', content: '同步完成' });
```

| API | 说明 |
|-----|------|
| `ToastHost` | 固定右下角；订阅总线 |
| `showToast({ status, content, duration })` | 弹出一条（覆盖上一条） |

`status`：`success` `error` `warning` `info`。默认 `duration` 2800ms。
