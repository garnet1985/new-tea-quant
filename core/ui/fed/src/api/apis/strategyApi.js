/**
 * 策略相关 API（当前为 mock，后续可替换为真实 BFF 请求）。
 * 行字段与 userspace/strategies/xxx 下 settings（StrategyMetaSettings）一致：name、description、is_enabled。
 */

const MOCK_STRATEGY_LIST = [
  {
    id: 'example',
    name: 'example',
    description: 'NTQ 内置 example 演示策略，对应 userspace/strategies/example 与 settings 中 meta 段。',
    is_enabled: true,
  },
  {
    id: 'template',
    name: 'template',
    description: '占位示例：展示「已禁用」状态（is_enabled: false）在列表中的呈现。',
    is_enabled: false,
  },
];

/**
 * 获取已发现策略列表
 * @returns {Promise<{ data: object[] }>}
 */
export function fetchStrategyList() {
  return new Promise((resolve) => {
    window.setTimeout(() => {
      resolve({ data: MOCK_STRATEGY_LIST.map((r) => ({ ...r })) });
    }, 400);
  });
}

/** 构建策略调试页路径（与路由定义保持一致） */
export function getStrategyConsolePath(strategyName) {
  return `/strategy-workbench/${encodeURIComponent(strategyName)}`;
}
