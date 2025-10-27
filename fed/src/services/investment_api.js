/**
 * 投资跟踪 API
 */
const API_BASE = 'http://localhost:5001/api/investment';

export const fetchStrategies = async () => {
  const response = await fetch(`${API_BASE}/strategies`);
  return await response.json();
};

export const fetchAllOpenTrades = async () => {
  const response = await fetch(`${API_BASE}/trades`);
  return await response.json();
};

export const fetchTradeDetail = async (tradeId) => {
  const response = await fetch(`${API_BASE}/trades/${tradeId}`);
  return await response.json();
};

export const createNewTrade = async (tradeData) => {
  const response = await fetch(`${API_BASE}/trades`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(tradeData),
  });
  return await response.json();
};

export const createOperation = async (tradeId, operationData) => {
  const response = await fetch(`${API_BASE}/trades/${tradeId}/operations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(operationData),
  });
  return await response.json();
};

export const addOperation = createOperation; // 兼容别名

export const updateTrade = async (tradeId, tradeData) => {
  const response = await fetch(`${API_BASE}/trades/${tradeId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(tradeData),
  });
  return await response.json();
};

export const deleteTrade = async (tradeId) => {
  const response = await fetch(`${API_BASE}/trades/${tradeId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  return await response.json();
};

export const updateOperation = async (tradeId, operationId, operationData) => {
  const response = await fetch(`${API_BASE}/trades/${tradeId}/operations/${operationId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(operationData),
  });
  return await response.json();
};

export const deleteOperation = async (tradeId, operationId) => {
  const response = await fetch(`${API_BASE}/trades/${tradeId}/operations/${operationId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  return await response.json();
};

