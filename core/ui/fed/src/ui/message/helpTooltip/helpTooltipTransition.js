import React from 'react';
import { Transition } from 'react-transition-group';

export const HELP_TOOLTIP_TRANSITION_MS = 220;
/** @deprecated 旧名 */
export const NTQ_HELP_TOOLTIP_TRANSITION_MS = HELP_TOOLTIP_TRANSITION_MS;

/**
 * Tooltip 浮入：默认从下方滑入（placement 为 top 时气泡在触发器上方）。
 */
const HelpTooltipTransition = React.forwardRef(function HelpTooltipTransition(props, ref) {
  const {
    children,
    in: inProp,
    onEnter,
    onExited,
    placement = 'top',
    timeout = HELP_TOOLTIP_TRANSITION_MS,
    ...other
  } = props;

  const nodeRef = React.useRef(null);
  const fromBottom = !String(placement).startsWith('bottom');
  const slideClass = fromBottom
    ? 'ntq-help-tooltip-transition--from-bottom'
    : 'ntq-help-tooltip-transition--from-top';

  return (
    <Transition
      nodeRef={nodeRef}
      appear
      in={inProp}
      timeout={timeout}
      onEnter={onEnter}
      onExited={onExited}
      {...other}
    >
      {(state) => (
        <div
          ref={(node) => {
            nodeRef.current = node;
            if (typeof ref === 'function') ref(node);
            else if (ref) ref.current = node;
          }}
          className={[
            'ntq-help-tooltip-transition',
            slideClass,
            `ntq-help-tooltip-transition--${state}`,
          ].filter(Boolean).join(' ')}
        >
          {children}
        </div>
      )}
    </Transition>
  );
});

export default HelpTooltipTransition;
