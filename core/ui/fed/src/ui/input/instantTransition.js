import React, { useLayoutEffect } from 'react';

/**
 * 无动画 Transition：在 layout 阶段触发 onEntering（供 Popover 算锚点），
 * 避免禁用 Grow 后菜单先出现在左上角再跳到触发器。
 */
const InstantTransition = React.forwardRef(function InstantTransition(props, ref) {
  const {
    in: inProp = false,
    appear, // eslint-disable-line no-unused-vars
    children,
    onEnter,
    onEntering,
    onEntered,
    onExit,
    onExiting,
    onExited,
    easing, // eslint-disable-line no-unused-vars
    style, // eslint-disable-line no-unused-vars
    timeout, // eslint-disable-line no-unused-vars
    mountOnEnter, // eslint-disable-line no-unused-vars
    unmountOnExit, // eslint-disable-line no-unused-vars
    addEndListener, // eslint-disable-line no-unused-vars
    ...rest
  } = props;

  useLayoutEffect(() => {
    if (inProp) {
      onEnter?.(null, true);
      onEntering?.(null, true);
      onEntered?.(null, true);
    } else {
      onExit?.(null);
      onExiting?.(null);
      onExited?.(null);
    }
    // 仅跟随开关联动；避免 MUI 每次渲染换回调导致重复定位
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inProp]);

  if (!inProp || !React.isValidElement(children)) {
    return null;
  }

  return React.cloneElement(children, {
    ...rest,
    ref: (node) => {
      if (typeof ref === 'function') ref(node);
      else if (ref) ref.current = node;
      const childRef = children.ref;
      if (typeof childRef === 'function') childRef(node);
      else if (childRef) childRef.current = node;
    },
  });
});

export default InstantTransition;
