const STORAGE_KEY = 'ntq.assistant.dock.v1';
const MAX_MESSAGES = 40;

function emptyStore() {
  return { chats: {}, selectedId: '' };
}

export function loadDockStore() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyStore();
    const data = JSON.parse(raw);
    if (!data || typeof data !== 'object') return emptyStore();
    const chats = data.chats && typeof data.chats === 'object' ? data.chats : {};
    return {
      chats,
      selectedId: String(data.selectedId || ''),
    };
  } catch {
    return emptyStore();
  }
}

function writeDockStore(store) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch {
    // quota / private mode — ignore
  }
}

export function readDockChat(providerId) {
  if (!providerId) return [];
  const entry = loadDockStore().chats[providerId];
  return Array.isArray(entry?.messages) ? entry.messages : [];
}

export function persistDockChat(providerId, messages) {
  if (!providerId) return;
  const store = loadDockStore();
  const serializable = (Array.isArray(messages) ? messages : [])
    .filter((item) => item && !item.pending && (item.role === 'user' || item.role === 'assistant') && item.content)
    .map((item) => ({
      id: item.id,
      role: item.role,
      content: String(item.content || ''),
      error: Boolean(item.error),
      mode: item.mode || undefined,
      catfoodSpent: item.catfoodSpent == null ? undefined : item.catfoodSpent,
    }))
    .slice(-MAX_MESSAGES);
  store.chats[providerId] = {
    messages: serializable,
    updatedAt: Date.now(),
  };
  writeDockStore(store);
}

export function clearDockChat(providerId) {
  if (!providerId) return;
  const store = loadDockStore();
  delete store.chats[providerId];
  writeDockStore(store);
}

export function persistDockSelectedId(selectedId) {
  const store = loadDockStore();
  store.selectedId = String(selectedId || '');
  writeDockStore(store);
}

/**
 * @param {Array<{ role: string, content: string, mode?: string, catfoodSpent?: number, error?: boolean }>} rows
 * @param {{ idRef: { current: number } }} opts
 */
export function hydrateMessages(rows, { idRef }) {
  const list = [];
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    if (!row || !row.content) return;
    const role = row.role === 'user' ? 'user' : 'assistant';
    const id = row.id != null && Number.isFinite(Number(row.id))
      ? Number(row.id)
      : (() => {
        const value = idRef.current;
        idRef.current += 1;
        return value;
      })();
    if (id >= idRef.current) idRef.current = id + 1;
    list.push({
      id,
      role,
      content: String(row.content),
      error: Boolean(row.error),
      mode: row.mode,
      catfoodSpent: row.catfoodSpent,
    });
  });
  return list;
}

export function isHeavyContext(messages) {
  const usable = (Array.isArray(messages) ? messages : []).filter(
    (item) => item && !item.pending && !item.error && item.content,
  );
  const chars = usable.reduce((sum, item) => sum + String(item.content).length, 0);
  const turns = usable.filter((item) => item.role === 'user').length;
  return turns >= 6 || chars >= 6000;
}
