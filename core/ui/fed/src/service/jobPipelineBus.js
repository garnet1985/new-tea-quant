/** 轻量总线：JobPipelineWatch 广播最新管道快照，供管道坞订阅。 */

const listeners = new Set();
let latest = {
  busy: false,
  job: null,
  jobs: [],
  pending: [],
  pending_count: 0,
};

export function publishPipelineSnapshot(snapshot) {
  latest = snapshot && typeof snapshot === 'object'
    ? snapshot
    : {
      busy: false,
      job: null,
      jobs: [],
      pending: [],
      pending_count: 0,
    };
  listeners.forEach((fn) => {
    try {
      fn(latest);
    } catch (_) {
      /* ignore subscriber errors */
    }
  });
}

export function getPipelineSnapshot() {
  return latest;
}

export function subscribePipelineSnapshot(fn) {
  listeners.add(fn);
  try {
    fn(latest);
  } catch (_) {
    /* ignore */
  }
  return () => {
    listeners.delete(fn);
  };
}
