import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import PropTypes from 'prop-types';

const LOGO_SRC = '/logo.png';
const HEADER_PX = 64;
const HOLD_MS = 140;
const LASER_MS = 620;
const LOGO_START_MS = HOLD_MS + LASER_MS - 40;
const LOGO_MS = 480;
const LOGO_DONE_MS = LOGO_START_MS + LOGO_MS;
const GLOW_FADE_MS = 1100;
const START_SCALE = 0.38;
const TOTAL_MS = LOGO_DONE_MS + GLOW_FADE_MS;
const MAX_FRAME_MS = 32;

function clamp01(value) {
  return Math.max(0, Math.min(1, value));
}

function easeOutCubic(t) {
  return 1 - (1 - t) ** 3;
}

function easeInCubic(t) {
  return t * t * t;
}

function fitCanvas(canvas) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(1, window.innerWidth);
  const height = Math.max(1, window.innerHeight - HEADER_PX);
  canvas.style.top = `${HEADER_PX}px`;
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  const pixelW = Math.floor(width * dpr);
  const pixelH = Math.floor(height * dpr);
  if (canvas.width !== pixelW || canvas.height !== pixelH) {
    canvas.width = pixelW;
    canvas.height = pixelH;
  }
  const ctx = canvas.getContext('2d', { alpha: true });
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, width, height };
}

function measureLogo(logoEl, canvasEl, width, height) {
  const fallback = {
    x: width * 0.5 - 84,
    y: height * 0.38 - 84,
    w: 168,
    h: 168,
    cx: width * 0.5,
    cy: height * 0.38,
  };
  if (!logoEl || !canvasEl) return fallback;
  const logoBox = logoEl.getBoundingClientRect();
  const canvasBox = canvasEl.getBoundingClientRect();
  if (logoBox.width < 8 || logoBox.height < 8) return fallback;
  const cx = logoBox.left - canvasBox.left + logoBox.width / 2;
  const cy = logoBox.top - canvasBox.top + logoBox.height / 2;
  return {
    x: logoBox.left - canvasBox.left,
    y: logoBox.top - canvasBox.top,
    w: logoBox.width,
    h: logoBox.height,
    cx,
    cy: Math.min(Math.max(cy, 48), height - 48),
  };
}

function makeBloomSprite(source) {
  const sprite = document.createElement('canvas');
  sprite.width = source.width;
  sprite.height = source.height;
  const ctx = sprite.getContext('2d');
  ctx.drawImage(source, 0, 0);
  ctx.globalCompositeOperation = 'source-in';
  const tint = ctx.createLinearGradient(0, 0, sprite.width, sprite.height);
  tint.addColorStop(0, '#a855f7');
  tint.addColorStop(0.5, '#22d3ee');
  tint.addColorStop(1, '#22c55e');
  ctx.fillStyle = tint;
  ctx.fillRect(0, 0, sprite.width, sprite.height);
  return sprite;
}

function scaledRect(logo, scale) {
  const w = logo.w * scale;
  const h = logo.h * scale;
  return {
    x: logo.cx - w / 2,
    y: logo.cy - h / 2,
    w,
    h,
  };
}

function drawBeam(ctx, x0, y0, x1, y1, color, power) {
  if (power <= 0) return;
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  ctx.strokeStyle = color;
  ctx.globalAlpha = 0.22 * power;
  ctx.lineWidth = 28;
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.lineTo(x1, y1);
  ctx.stroke();

  ctx.globalAlpha = 0.55 * power;
  ctx.lineWidth = 10;
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.lineTo(x1, y1);
  ctx.stroke();

  ctx.strokeStyle = '#ffffff';
  ctx.globalAlpha = 0.95 * power;
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.lineTo(x1, y1);
  ctx.stroke();

  ctx.globalAlpha = power;
  ctx.fillStyle = '#ffffff';
  ctx.beginPath();
  ctx.arc(x1, y1, 4, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

const SPARK_COLORS = ['#22d3ee', '#a855f7', '#ffffff', '#22c55e'];

function drawLogoGlow(ctx, bloom, box, intensity, expand) {
  if (!bloom || intensity <= 0) return;
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  const rings = [
    { pad: 10, alpha: 0.95 },
    { pad: 22, alpha: 0.5 },
    { pad: 38, alpha: 0.26 },
  ];
  rings.forEach((ring) => {
    const pad = ring.pad * expand;
    ctx.globalAlpha = ring.alpha * intensity;
    ctx.drawImage(
      bloom,
      box.x - pad,
      box.y - pad,
      box.w + pad * 2,
      box.h + pad * 2,
    );
  });
  ctx.restore();
}

function glowEnvelope(elapsed, reveal) {
  if (elapsed < LOGO_START_MS) return 0;
  if (elapsed < LOGO_DONE_MS) return reveal;
  return 1 - easeOutCubic(clamp01((elapsed - LOGO_DONE_MS) / GLOW_FADE_MS));
}

function makeSpark(cx, cy, logoW, logoH) {
  const angle = Math.random() * Math.PI * 2;
  const edge = (Math.min(logoW, logoH) * 0.5) * (0.25 + Math.random() * 0.45);
  const speed = 220 + Math.random() * 420;
  return {
    x: cx + Math.cos(angle) * edge,
    y: cy + Math.sin(angle) * edge,
    vx: Math.cos(angle) * speed,
    vy: Math.sin(angle) * speed,
    life: 0,
    maxLife: 520 + Math.random() * 640,
    size: 2.4 + Math.random() * 3.2,
    color: SPARK_COLORS[(Math.random() * SPARK_COLORS.length) | 0],
  };
}

function stepSparks(sparks, dt, cx, cy, logoW, logoH, burstLeft) {
  if (burstLeft > 0) {
    const n = Math.min(burstLeft, 14);
    for (let i = 0; i < n; i += 1) sparks.push(makeSpark(cx, cy, logoW, logoH));
    burstLeft -= n;
  }

  for (let i = sparks.length - 1; i >= 0; i -= 1) {
    const spark = sparks[i];
    spark.life += dt;
    spark.x += spark.vx * (dt / 1000);
    spark.y += spark.vy * (dt / 1000);
    spark.vx *= 0.992;
    spark.vy *= 0.992;
    if (spark.life >= spark.maxLife) sparks.splice(i, 1);
  }
  return burstLeft;
}

function drawSparks(ctx, sparks) {
  if (!sparks.length) return;
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.lineCap = 'round';
  sparks.forEach((spark) => {
    const t = Math.max(0, 1 - spark.life / spark.maxLife);
    const radius = spark.size * (0.7 + 0.5 * t);
    ctx.fillStyle = spark.color;
    ctx.globalAlpha = 0.35 * t;
    ctx.beginPath();
    ctx.arc(spark.x, spark.y, radius * 2.4, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 0.95 * t;
    ctx.beginPath();
    ctx.arc(spark.x, spark.y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.globalAlpha = 0.9 * t;
    ctx.beginPath();
    ctx.arc(spark.x, spark.y, radius * 0.4, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = spark.color;
    ctx.globalAlpha = 0.85 * t;
    ctx.lineWidth = Math.max(1.4, radius * 0.7);
    ctx.beginPath();
    ctx.moveTo(spark.x, spark.y);
    ctx.lineTo(spark.x - spark.vx * 0.045, spark.y - spark.vy * 0.045);
    ctx.stroke();
  });
  ctx.restore();
}

function drawImpact(ctx, x, y, amount) {
  if (amount <= 0) return;
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  const radius = 24 + amount * 90;
  const glow = ctx.createRadialGradient(x, y, 0, x, y, radius);
  glow.addColorStop(0, `rgba(255,255,255,${0.62 * amount})`);
  glow.addColorStop(0.22, `rgba(34,211,238,${0.36 * amount})`);
  glow.addColorStop(0.55, `rgba(168,85,247,${0.18 * amount})`);
  glow.addColorStop(1, 'rgba(34,211,238,0)');
  ctx.fillStyle = glow;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

/**
 * 挂到 document.body，按真实帧时长推进，避免首帧卡顿把激光整段跳过。
 */
function WelcomeIntroCanvas({ logoRef, onPageReveal, onDone }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    let raf = 0;
    let stopped = false;
    let elapsed = 0;
    let lastNow = 0;
    let source = null;
    let bloom = null;
    let pageRevealed = false;
    let sparks = [];
    let burstLeft = 0;
    let burstArmed = true;

    const tick = (now) => {
      if (stopped) return;
      const { ctx, width, height } = fitCanvas(canvas);
      let dt = 16;
      if (!lastNow) {
        lastNow = now;
        dt = 16;
      } else {
        dt = Math.min(MAX_FRAME_MS, Math.max(0, now - lastNow));
        elapsed += dt;
        lastNow = now;
      }

      const logo = measureLogo(logoRef.current, canvas, width, height);
      const laser = easeInCubic(clamp01((elapsed - HOLD_MS) / LASER_MS));
      const reveal = easeOutCubic(clamp01((elapsed - LOGO_START_MS) / LOGO_MS));
      const overlay = reveal <= 0 ? 1 : 1 - reveal;
      const scale = START_SCALE + (1 - START_SCALE) * reveal;
      const impact = easeOutCubic(clamp01((elapsed - (HOLD_MS + LASER_MS)) / 180));
      const glow = glowEnvelope(elapsed, reveal);
      const expand = 0.3 + easeOutCubic(clamp01((elapsed - (HOLD_MS + LASER_MS)) / 420)) * 1.25;

      if (burstArmed && elapsed >= HOLD_MS + LASER_MS) {
        burstArmed = false;
        burstLeft = 64;
      }
      burstLeft = stepSparks(
        sparks,
        dt,
        logo.cx,
        logo.cy,
        logo.w,
        logo.h,
        burstLeft,
      );

      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = `rgba(6, 6, 18, ${overlay})`;
      ctx.fillRect(0, 0, width, height);

      const leftX = logo.cx * laser;
      const rightX = width - (width - logo.cx) * laser;
      const beamPower = laser < 1 ? 1 : overlay;
      drawBeam(ctx, 0, logo.cy, leftX, logo.cy, '#22d3ee', beamPower);
      drawBeam(ctx, width, logo.cy, rightX, logo.cy, '#a855f7', beamPower);
      drawImpact(ctx, logo.cx, logo.cy, impact * overlay);

      drawSparks(ctx, sparks);

      if (reveal > 0.01 && source) {
        const box = scaledRect(logo, scale);
        drawLogoGlow(ctx, bloom, box, glow, expand);
        ctx.save();
        ctx.globalAlpha = reveal;
        ctx.drawImage(source, box.x, box.y, box.w, box.h);
        ctx.restore();
      }

      if (!pageRevealed && elapsed >= LOGO_DONE_MS) {
        pageRevealed = true;
        onPageReveal();
      }

      if (elapsed >= TOTAL_MS) {
        onDone();
        return;
      }
      raf = window.requestAnimationFrame(tick);
    };

    const startLoop = () => {
      if (stopped || raf) return;
      raf = window.requestAnimationFrame(tick);
    };

    const image = new Image();
    image.decoding = 'async';
    image.src = LOGO_SRC;
    image.onload = () => {
      if (stopped) return;
      source = image;
      try {
        bloom = makeBloomSprite(image);
      } catch {
        bloom = null;
      }
    };
    image.onerror = () => {};

    startLoop();

    return () => {
      stopped = true;
      window.cancelAnimationFrame(raf);
    };
  }, [logoRef, onDone, onPageReveal]);

  return createPortal(
    <canvas ref={canvasRef} className="welcome-intro-canvas" aria-hidden />,
    document.body,
  );
}

WelcomeIntroCanvas.propTypes = {
  logoRef: PropTypes.shape({ current: PropTypes.any }).isRequired,
  onPageReveal: PropTypes.func.isRequired,
  onDone: PropTypes.func.isRequired,
};

export default WelcomeIntroCanvas;
