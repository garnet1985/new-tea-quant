/**
 * 盈亏色随 market_profile.ui.pnl_polarity：
 * - cn：红赚绿亏（A 股习惯）
 * - intl：绿赚红亏
 */

const RED = '#FF4D67';
const RED_MUTED = '#FF8A65';
const GREEN = '#00D9A5';
const GREEN_MUTED = '#66BB6A';
const BUY = '#00E5FF';
const SELL = '#FF9100';
const NEUTRAL = '#90A4AE';

/** 已知 profile → polarity；与 market_profile.settings.ui 对齐。 */
const PROFILE_POLARITY = {
  china_a_stock: 'cn',
  hong_kong: 'intl',
  us_stock: 'intl',
  forex: 'intl',
  crypto: 'intl',
  commodity_future: 'intl',
};

function buildPalette(polarity) {
  const isCn = polarity !== 'intl';
  const profit = isCn ? RED : GREEN;
  const loss = isCn ? GREEN : RED;
  const profitMuted = isCn ? RED_MUTED : GREEN_MUTED;
  const lossMuted = isCn ? GREEN_MUTED : RED_MUTED;
  return {
    polarity: isCn ? 'cn' : 'intl',
    profit,
    loss,
    profitMuted,
    lossMuted,
    buy: BUY,
    sell: SELL,
    neutral: NEUTRAL,
    candleUp: profit,
    candleDown: loss,
    /** RGB 阴影片段，给 pin 用 */
    shadow: {
      buy: '0, 229, 255',
      profit: isCn ? '255, 77, 103' : '0, 217, 165',
      loss: isCn ? '0, 217, 165' : '255, 77, 103',
      profitMuted: isCn ? '255, 138, 101' : '102, 187, 106',
      lossMuted: isCn ? '102, 187, 106' : '255, 138, 101',
      sell: '255, 145, 0',
      neutral: '144, 164, 174',
    },
  };
}

export function resolvePnlPolarity(marketProfileOrPolarity) {
  const raw = String(marketProfileOrPolarity || '').trim().toLowerCase();
  if (raw === 'cn' || raw === 'intl') return raw;
  if (PROFILE_POLARITY[raw]) return PROFILE_POLARITY[raw];
  return 'cn';
}

export function resolveMarketPnlPalette(marketProfileOrPolarity) {
  return buildPalette(resolvePnlPolarity(marketProfileOrPolarity));
}

export const DEFAULT_MARKET_PNL_PALETTE = buildPalette('cn');
