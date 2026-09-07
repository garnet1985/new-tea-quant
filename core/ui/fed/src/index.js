import React from 'react';
import { createRoot } from 'react-dom/client';
import './assets/scss/main.scss';
import './index.css';
import App from './app';

const rootEl = document.getElementById('root');
createRoot(rootEl).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
