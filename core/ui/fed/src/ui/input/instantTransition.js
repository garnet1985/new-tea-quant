import React, { useLayoutEffect, useRef } from 'react';

/**
 * 无动画 Transition：在 layout 阶段用真实 DOM 节点触发 onEntering（供 Popover 算锚点 / 滚动条），
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

  const nodeRef = useRef(null);

  useLayoutEffect(() => {
    const node = nodeRef.current;
    if (inProp) {
      // MUI Menu/Popover 的 handleEntering → adjustStyleForScrollbar 需要真实节点
      if (!node) return;
      onEnter?.(node, true);
      onEntering?.(node, true);
      onEntered?.(node, true);
    } else {
      onExit?.(node);
      onExiting?.(node);
      onExited?.(node);
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
      nodeRef.current = node;
      if (typeof ref === 'function') ref(node);
      else if (ref) ref.current = node;
      const childRef = children.ref;
      if (typeof childRef === 'function') childRef(node);
      else if (childRef) childRef.current = node;
    },
  });
});

export default InstantTransition;
