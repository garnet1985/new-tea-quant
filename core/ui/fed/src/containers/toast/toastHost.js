import React, { useEffect, useState } from 'react';
import Message from 'views/message';
import { subscribeToast } from './toastBus';
import './style.scss';

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
      <Message severity={item.severity} onClose={() => setItem(null)}>
        {item.content}
      </Message>
    </div>
  );
}

export default ToastHost;
