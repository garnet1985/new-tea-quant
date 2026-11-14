import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  CircularProgress,
  Collapse,
  IconButton,
  LinearProgress,
  Link,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { abandonPipelineJob, cancelPipelineJob } from 'api/runtimeApi';
import { showToast } from 'containers/toast';
import { jobDeepLink, jobDisplayName } from 'service/jobPipelineLinks';
import { publishPipelineSnapshot, subscribePipelineSnapshot } from 'service/jobPipelineBus';
import { dismissUnreadJob, subscribeUnreadJobs } from 'service/jobPipelineUnread';
import logClientError from 'service/logClientError';
import NtqIcon from 'views/ntqIcon';
import './style.scss';

function statusKey(row) {
  if (row?.cancel_requested) return 'cancelling';
  return String(row?.status || '').trim().toLowerCase() || '';
}

function statusLabel(row) {
  const s = statusKey(row);
  if (s === 'cancelling') return '取消中';
  if (s === 'stale') return '超时';
  if (s === 'running') return '运行中';
  if (s === 'pending') return '排队中';
  if (s === 'completed') return '成功';
  if (s === 'failed') return '失败';
  if (s === 'cancelled') return '取消';
  return s || '—';
}

function statusClass(row) {
  const s = statusKey(row);
  if (s === 'cancelling' || s === 'cancelled') return 'ntq-job-pipeline-dock__status--cancelling';
  if (s === 'stale') return 'ntq-job-pipeline-dock__status--stale';
  if (s === 'pending') return 'ntq-job-pipeline-dock__status--pending';
  if (s === 'completed') return 'ntq-job-pipeline-dock__status--completed';
  if (s === 'failed') return 'ntq-job-pipeline-dock__status--failed';
  return 'ntq-job-pipeline-dock__status--running';
}

function progressPercent(row) {
  const pct = Number(row?.progress?.percent);
  if (!Number.isFinite(pct)) return null;
  return Math.max(0, Math.min(100, pct));
}

function parseTimeMs(value) {
  if (value == null || value === '') return null;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  const raw = String(value).trim();
  if (!raw) return null;
  if (/^\d+$/.test(raw)) {
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }
  const ms = Date.parse(raw);
  return Number.isFinite(ms) ? ms : null;
}

/** 墙钟已运行时长；完成后冻结到 finished_at。 */
function formatElapsed(row, nowMs) {
  const start = parseTimeMs(row?.started_at);
  if (start == null) return '—';
  const s = statusKey(row);
  const ended = s === 'running' || s === 'stale' || s === 'cancelling' || s === 'pending'
    ? nowMs
    : (parseTimeMs(row?.finished_at) ?? nowMs);
  const sec = Math.max(0, Math.floor((ended - start) / 1000));
  if (sec < 60) return `${sec}s`;
  const mins = Math.floor(sec / 60);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  const rem = mins % 60;
  return rem > 0 ? `${hours}h${rem}m` : `${hours}h`;
}

function JobPipelineDock() {
  const [snap, setSnap] = useState(null);
  const [unread, setUnread] = useState([]);
  const [open, setOpen] = useState(false);
  const [cancellingId, setCancellingId] = useState('');
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => subscribePipelineSnapshot(setSnap), []);
  useEffect(() => subscribeUnreadJobs(setUnread), []);

  const activeJobs = useMemo(() => {
    if (Array.isArray(snap?.jobs) && snap.jobs.length) return snap.jobs;
    const rows = [];
    if (snap?.job) rows.push(snap.job);
    if (Array.isArray(snap?.pending)) rows.push(...snap.pending);
    return rows;
  }, [snap]);

  const jobs = useMemo(() => {
    const activeIds = new Set(activeJobs.map((row) => String(row?.job_id || '')).filter(Boolean));
    const unreadRows = unread.filter((row) => !activeIds.has(String(row?.job_id || '')));
    return [...activeJobs, ...unreadRows];
  }, [activeJobs, unread]);

  const hasLiveElapsed = useMemo(
    () => jobs.some((row) => {
      const s = statusKey(row);
      return s === 'running' || s === 'stale' || s === 'cancelling' || s === 'pending';
    }),
    [jobs],
  );

  useEffect(() => {
    if (!open && !hasLiveElapsed) return undefined;
    setNowMs(Date.now());
    const timerId = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timerId);
  }, [open, hasLiveElapsed]);

  const pendingCount = Number(snap?.pending_count || 0)
    || activeJobs.filter((row) => String(row?.status || '') === 'pending').length;
  const running = snap?.job
    || activeJobs.find((row) => {
      const s = String(row?.status || '');
      return s === 'running' || s === 'stale';
    })
    || null;
  const unreadCount = unread.length;

  const handleCancel = useCallback(async (jobId) => {
    const id = String(jobId || '').trim();
    if (!id || cancellingId) return;
    setCancellingId(id);
    try {
      const out = await cancelPipelineJob(id);
      if (out?.pipeline) publishPipelineSnapshot(out.pipeline);
      showToast({
        severity: 'info',
        duration: 3200,
        content: out?.reason || '已从队列取消该任务',
      });
    } catch (error) {
      logClientError('jobPipelineDock.cancel', error, id);
      showToast({
        severity: 'error',
        duration: 4200,
        content: error?.message || '取消失败',
      });
    } finally {
      setCancellingId('');
    }
  }, [cancellingId]);

  const handleAbandon = useCallback(async (jobId) => {
    const id = String(jobId || '').trim();
    if (!id || cancellingId) return;
    setCancellingId(id);
    try {
      const out = await abandonPipelineJob(id);
      if (out?.pipeline) publishPipelineSnapshot(out.pipeline);
      showToast({
        severity: 'info',
        duration: 3200,
        content: out?.reason || '已取消该任务，管道已释放',
      });
    } catch (error) {
      logClientError('jobPipelineDock.abandon', error, id);
      showToast({
        severity: 'error',
        duration: 4200,
        content: error?.message || '取消失败',
      });
    } finally {
      setCancellingId('');
    }
  }, [cancellingId]);

  const handleView = useCallback((jobId) => {
    dismissUnreadJob(jobId);
    setOpen(false);
  }, []);

  let markerText = '无任务';
  if (running) {
    if (String(running.status || '') === 'stale') {
      markerText = pendingCount > 0 ? `超时 · 排队 ${pendingCount}` : '超时';
    } else if (running.cancel_requested) {
      markerText = '取消中';
    } else {
      const pct = Number(running?.progress?.percent);
      const runLabel = Number.isFinite(pct) && pct > 0 ? `运行中 ${pct}%` : '运行中';
      markerText = pendingCount > 0 ? `${runLabel} · 排队 ${pendingCount}` : runLabel;
    }
  } else if (pendingCount > 0) {
    markerText = `排队 ${pendingCount}`;
  } else if (unreadCount > 0) {
    markerText = unreadCount > 1 ? `待查看 · ${unreadCount}` : '待查看';
  }

  return (
    <Box className="ntq-job-pipeline-dock">
      <Collapse in={open} timeout={180} unmountOnExit>
        <Paper elevation={0} className="ntq-job-pipeline-dock__panel">
          <Box className="ntq-job-pipeline-dock__panel-head">
            <Typography variant="subtitle2" className="ntq-job-pipeline-dock__panel-title">
              任务管道
            </Typography>
            <IconButton
              size="small"
              aria-label="收起管道"
              onClick={() => setOpen(false)}
            >
              <NtqIcon name="expandMore" size={18} />
            </IconButton>
          </Box>
          {jobs.length === 0 ? (
            <Typography variant="body2" className="ntq-job-pipeline-dock__empty">
              当前没有运行、排队或待查看的任务
            </Typography>
          ) : (
            <Table size="small" className="ntq-job-pipeline-dock__table">
              <TableHead>
                <TableRow>
                  <TableCell>任务</TableCell>
                  <TableCell width={72}>状态</TableCell>
                  <TableCell width={88}>进度</TableCell>
                  <TableCell width={64}>已运行</TableCell>
                  <TableCell width={72}>页面</TableCell>
                  <TableCell width={64} align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {jobs.map((row) => {
                  const id = String(row.job_id || '');
                  const key = statusKey(row);
                  const pending = key === 'pending';
                  const completed = key === 'completed';
                  const stale = key === 'stale';
                  const live = key === 'running' || stale || key === 'cancelling';
                  const href = jobDeepLink(row);
                  const name = jobDisplayName(row);
                  const detail = String(row?.progress?.detail || '').trim();
                  const pct = live ? progressPercent(row) : (completed ? progressPercent(row) : null);
                  const showBar = pct != null && (live || completed);
                  return (
                    <TableRow key={id || `${row.kind}-${row.resource_key}-${key}`}>
                      <TableCell>
                        <Typography
                          variant="body2"
                          className="ntq-job-pipeline-dock__job-name"
                          title={name}
                        >
                          {name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <span className={['ntq-job-pipeline-dock__status', statusClass(row)].join(' ')}>
                          {statusLabel(row)}
                        </span>
                      </TableCell>
                      <TableCell>
                        {showBar ? (
                          <Box
                            className="ntq-job-pipeline-dock__progress"
                            title={detail || `${pct}%`}
                          >
                            <LinearProgress
                              variant="determinate"
                              value={pct}
                              className="ntq-job-pipeline-dock__progress-bar"
                            />
                          </Box>
                        ) : (
                          <span className="ntq-job-pipeline-dock__empty-cell">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="ntq-job-pipeline-dock__elapsed">
                          {formatElapsed(row, nowMs)}
                        </span>
                      </TableCell>
                      <TableCell>
                        {href ? (
                          <Link
                            component={RouterLink}
                            to={href}
                            underline="hover"
                            className="ntq-job-pipeline-dock__job-link"
                            onClick={() => {
                              if (completed) handleView(id);
                              else setOpen(false);
                            }}
                          >
                            进入页面
                          </Link>
                        ) : (
                          <span className="ntq-job-pipeline-dock__empty-cell">—</span>
                        )}
                      </TableCell>
                      <TableCell align="right">
                        {pending || (key === 'running' && !row?.cancel_requested) ? (
                          <Button
                            size="small"
                            color="inherit"
                            disabled={Boolean(cancellingId)}
                            onClick={() => handleCancel(id)}
                          >
                            {cancellingId === id ? '取消中…' : '取消'}
                          </Button>
                        ) : null}
                        {stale ? (
                          <Button
                            size="small"
                            color="inherit"
                            disabled={Boolean(cancellingId)}
                            onClick={() => handleAbandon(id)}
                          >
                            {cancellingId === id ? '取消中…' : '取消'}
                          </Button>
                        ) : null}
                        {completed && !href ? (
                          <Button
                            size="small"
                            color="inherit"
                            onClick={() => dismissUnreadJob(id)}
                          >
                            知道了
                          </Button>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </Paper>
      </Collapse>

      <button
        type="button"
        className={[
          'ntq-job-pipeline-dock__marker',
          open ? 'ntq-job-pipeline-dock__marker--open' : '',
          running && String(running.status || '') === 'stale'
            ? 'ntq-job-pipeline-dock__marker--stale'
            : '',
          running && String(running.status || '') !== 'stale'
            ? 'ntq-job-pipeline-dock__marker--running'
            : '',
          !running && pendingCount > 0 ? 'ntq-job-pipeline-dock__marker--pending' : '',
          !running && pendingCount === 0 && unreadCount > 0
            ? 'ntq-job-pipeline-dock__marker--unread'
            : '',
        ].filter(Boolean).join(' ')}
        aria-expanded={open}
        aria-label="打开任务管道"
        onClick={() => setOpen((v) => !v)}
      >
        {running && String(running.status || '') !== 'stale' ? (
          <CircularProgress size={14} thickness={5} className="ntq-job-pipeline-dock__spin" />
        ) : (
          <NtqIcon name="syncAlt" size={16} className="ntq-job-pipeline-dock__marker-icon" />
        )}
        <span className="ntq-job-pipeline-dock__marker-text">{markerText}</span>
      </button>
    </Box>
  );
}

export default JobPipelineDock;
