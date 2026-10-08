import React, { useEffect, useMemo, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import AssistantMarkdown from './assistantMarkdown';

const CJK = /[\u4e00-\u9fff]/;
const WORD = /[a-zA-Z0-9_]/;

function prefersReducedMotion() {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function insideFence(text, index) {
  const marks = text.slice(0, index).match(/```/g);
  return Boolean(marks && marks.length % 2 === 1);
}

function unitsThisFrame(remaining) {
  if (remaining > 1800) return 10;
  if (remaining > 700) return 5;
  if (remaining > 180) return 2;
  return 1;
}

function advance(text, index, unitBudget) {
  const len = text.length;
  let i = index;
  let units = 0;
  while (i < len && units < unitBudget) {
    const rest = text.slice(i);
    if (insideFence(text, i)) {
      const nl = rest.indexOf('\n');
      i += nl === -1 ? rest.length : nl + 1;
      units += 1;
      continue;
    }
    const ch = text[i];
    if (CJK.test(ch)) {
      i += 1;
      units += 1;
      continue;
    }
    if (WORD.test(ch)) {
      const match = rest.match(/^[a-zA-Z0-9_]+/);
      i += match ? match[0].length : 1;
      units += 1;
      continue;
    }
    i += 1;
    if (text[i] === ' ') i += 1;
    units += 1;
  }
  return i;
}

function AssistantTypewriter({ text, animate, onProgress, onDone }) {
  const source = String(text || '');
  const reduceMotion = useMemo(() => prefersReducedMotion(), []);
  const shouldType = Boolean(animate) && !reduceMotion && source.length > 0;
  const [shownCount, setShownCount] = useState(() => (shouldType ? 0 : source.length));
  const skipRef = useRef(false);
  const onProgressRef = useRef(onProgress);
  const onDoneRef = useRef(onDone);

  onProgressRef.current = onProgress;
  onDoneRef.current = onDone;

  useEffect(() => {
    if (!shouldType) {
      setShownCount(source.length);
      return undefined;
    }
    skipRef.current = false;
    setShownCount(0);
    let index = 0;
    let frame = 0;
    let last = 0;
    const tick = (now) => {
      if (skipRef.current) return;
      if (now - last < 18) {
        frame = window.requestAnimationFrame(tick);
        return;
      }
      last = now;
      index = advance(source, index, unitsThisFrame(source.length - index));
      setShownCount(index);
      onProgressRef.current?.();
      if (index < source.length) {
        frame = window.requestAnimationFrame(tick);
      } else {
        onDoneRef.current?.();
      }
    };
    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, [source, shouldType]);

  const typing = shouldType && shownCount < source.length;
  const visible = source.slice(0, typing ? shownCount : source.length);

  const skip = () => {
    if (!typing) return;
    skipRef.current = true;
    setShownCount(source.length);
    onDoneRef.current?.();
  };

  return (
    <div
      className={['ntq-assistant-typewriter', typing ? 'is-typing' : ''].filter(Boolean).join(' ')}
      onClick={skip}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') skip();
      }}
      role={typing ? 'button' : undefined}
      tabIndex={typing ? 0 : undefined}
      title={typing ? '点击显示全文' : undefined}
    >
      <AssistantMarkdown text={visible} />
    </div>
  );
}

AssistantTypewriter.propTypes = {
  text: PropTypes.string,
  animate: PropTypes.bool,
  onProgress: PropTypes.func,
  onDone: PropTypes.func,
};

AssistantTypewriter.defaultProps = {
  text: '',
  animate: false,
  onProgress: undefined,
  onDone: undefined,
};

export default AssistantTypewriter;
