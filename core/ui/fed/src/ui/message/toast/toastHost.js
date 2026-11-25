import React, { useEffect, useState } from 'react';
import Message from 'ui/message/message';
import { subscribeToast } from './toastBus';
import './style.scss';

/**
 * 右下角 Toast 宿主。应用壳挂一次即可；图鉴可本地挂载演示。
 */
function ToastHost() {
  const [item, setItem] = useState(null);

  useEffect(() => subscribeToast(setItem), []);

  useEffect(() => {
    if (!item) return undefined;
    const timer = window.setTimeout(() => {
      setItem((current) => (current && current.id === item.id ? null : current));
    }, item.duration);
    return () => window.clearTimeout(timer);
  }, [item]);

  if (!item) return null;

  return (
    <div className="ntq-toast-host">
      <Message
        status={item.status}
        onClose={() => setItem(null)}
        className="ntq-toast-host__item"
      >
        {item.content}
      </Message>
    </div>
  );
}

export default ToastHost;
