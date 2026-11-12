import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  CircularProgress,
  Collapse,
  IconButton,
  Link,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { cancelPipelineJob } from 'api/runtimeApi';
import { showToast } from 'containers/toast';
import { jobDeepLink, jobDisplayName } from 'service/jobPipelineLinks';
import { publishPipelineSnapshot, subscribePipelineSnapshot } from 'service/jobPipelineBus';
import { dismissUnreadJob, subscribeUnreadJobs } from 'service/jobPipelineUnread';
import logClientError from 'service/logClientError';
import NtqIcon from 'views/ntqIcon';
import './style.scss';

function statusLabel(status) {
  const s = String(status || '').trim().toLowerCase();
  if (s === 'running') return '运行中';
  if (s === 'pending') return '排队中';
  if (s === 'completed') return '已完成';
  return s || '—';
}

function statusClass(status) {
  const s = String(status || '').trim().toLowerCase();
  if (s === 'pending') return 'ntq-job-pipeline-dock__status--pending';
  if (s === 'completed') return 'ntq-job-pipeline-dock__status--completed';
  return 'ntq-job-pipeline-dock__status--running';
}

function JobPipelineDock() {
  const [snap, setSnap] = useState(null);
  const [unread, setUnread] = useState([]);
  const [open, setOpen] = useState(false);
  const [cancellingId, setCancellingId] = useState('');

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

  const pendingCount = Number(snap?.pending_count || 0)
    || activeJobs.filter((row) => String(row?.status || '') === 'pending').length;
  const running = snap?.job || activeJobs.find((row) => String(row?.status || '') === 'running') || null;
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
        content: '已从队列取消该任务',
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

  const handleView = useCallback((jobId) => {
    dismissUnreadJob(jobId);
    setOpen(false);
  }, []);

  let markerText = '无任务';
  if (running) {
    markerText = pendingCount > 0 ? `运行中 · 排队 ${pendingCount}` : '运行中';
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
                  <TableCell width={88}>状态</TableCell>
                  <TableCell width={96} align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {jobs.map((row) => {
                  const id = String(row.job_id || '');
                  const status = String(row.status || '').trim().toLowerCase();
                  const pending = status === 'pending';
                  const completed = status === 'completed';
                  const href = jobDeepLink(row);
                  const name = jobDisplayName(row);
                  return (
                    <TableRow key={id || `${row.kind}-${row.resource_key}-${status}`}>
                      <TableCell>
                        <Typography variant="body2" className="ntq-job-pipeline-dock__job-name">
                          {name}
                        </Typography>
                        {!completed && href ? (
                          <Link
                            component={RouterLink}
                            to={href}
                            underline="hover"
                            className="ntq-job-pipeline-dock__job-link"
                            onClick={() => setOpen(false)}
                          >
                            打开
                          </Link>
                        ) : null}
                      </TableCell>
                      <TableCell>
                        <span className={['ntq-job-pipeline-dock__status', statusClass(status)].join(' ')}>
                          {statusLabel(status)}
                        </span>
                      </TableCell>
                      <TableCell align="right">
                        {pending ? (
                          <Button
                            size="small"
                            color="inherit"
                            disabled={Boolean(cancellingId)}
                            onClick={() => handleCancel(id)}
                          >
                            {cancellingId === id ? '取消中…' : '取消'}
                          </Button>
                        ) : null}
                        {completed && href ? (
                          <Link
                            component={RouterLink}
                            to={href}
                            underline="hover"
                            className="ntq-job-pipeline-dock__view-link"
                            onClick={() => handleView(id)}
                          >
                            查看
                          </Link>
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
                        {!pending && !completed ? (
                          <Typography variant="caption" color="text.secondary">
                            —
                          </Typography>
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
          running ? 'ntq-job-pipeline-dock__marker--running' : '',
          !running && pendingCount > 0 ? 'ntq-job-pipeline-dock__marker--pending' : '',
          !running && pendingCount === 0 && unreadCount > 0
            ? 'ntq-job-pipeline-dock__marker--unread'
            : '',
        ].filter(Boolean).join(' ')}
        aria-expanded={open}
        aria-label="打开任务管道"
        onClick={() => setOpen((v) => !v)}
      >
        {running ? (
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
