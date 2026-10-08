export function toPathParts(path) {
  return String(path || '')
    .split('.')
    .map((item) => item.trim())
    .filter(Boolean);
}

export function getByPath(obj, path) {
  const parts = toPathParts(path);
  let cursor = obj;
  for (let i = 0; i < parts.length; i += 1) {
    if (cursor == null) return undefined;
    cursor = cursor[parts[i]];
  }
  return cursor;
}

export function setByPath(obj, path, value) {
  const parts = toPathParts(path);
  if (parts.length === 0) return obj;
  const root = obj && typeof obj === 'object' ? { ...obj } : {};
  let cursor = root;
  for (let i = 0; i < parts.length - 1; i += 1) {
    const key = parts[i];
    cursor[key] = cursor[key] && typeof cursor[key] === 'object' ? { ...cursor[key] } : {};
    cursor = cursor[key];
  }
  cursor[parts[parts.length - 1]] = value;
  return root;
}

export function runFieldEvents(nextValue, field, changedValue) {
  const events = Array.isArray(field?.events) ? field.events : [];
  let result = nextValue;
  events.forEach((event) => {
    if (event?.on !== 'valueChange') return;
    const effects = Array.isArray(event?.effects) ? event.effects : [];
    effects.forEach((effect) => {
      if (effect?.type === 'setValue' && effect.target) {
        const effectValue = typeof effect.value === 'function'
          ? effect.value({ values: result, changedValue })
          : (effect.value ?? changedValue);
        result = setByPath(result, effect.target, effectValue);
      }
    });
  });
  return result;
}