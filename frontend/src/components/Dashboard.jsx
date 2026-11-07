import { useCallback, useEffect, useMemo, useState } from 'react';
import { formatLongDay, todayIst } from '../dates.js';
import PlannerBox from './PlannerBox.jsx';
import ProgressPanel from './ProgressPanel.jsx';
import TaskForm from './TaskForm.jsx';
import TaskSection from './TaskSection.jsx';

const PRIORITY_ORDER = { high: 0, medium: 1, low: 2 };
const byDueDate = (a, b) => a.dueDate.localeCompare(b.dueDate) || PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority];
const byCompletedLatest = (a, b) => (b.completedAt ?? '').localeCompare(a.completedAt ?? '');
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export default function Dashboard({ api, localMode, onSignOut }) {
  const [tasks, setTasks] = useState(null);
  const [progress, setProgress] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [progressError, setProgressError] = useState('');
  const [newIds, setNewIds] = useState(new Set());
  const today = todayIst();

  const refreshTasks = useCallback(async () => {
    const { tasks: latest } = await api.listTasks();
    setTasks(latest);
    return latest;
  }, [api]);

  const refreshProgress = useCallback(async () => {
    try {
      setProgress(await api.getProgress());
      setProgressError('');
    } catch (error) {
      setProgressError(error.message);
    }
  }, [api]);

  const refresh = useCallback(async () => {
    await Promise.all([refreshTasks(), refreshProgress()]);
  }, [refreshTasks, refreshProgress]);

  const load = useCallback(async () => {
    setLoadError('');
    try {
      await refresh();
    } catch (error) {
      setLoadError(error.message);
    }
  }, [refresh]);

  useEffect(() => {
    load();
  }, [load]);

  const { dueNow, upcoming, done } = useMemo(() => {
    const all = tasks ?? [];
    const open = all.filter((t) => t.status === 'todo').sort(byDueDate);
    return {
      dueNow: open.filter((t) => t.dueDate <= today),
      upcoming: open.filter((t) => t.dueDate > today),
      done: all.filter((t) => t.status === 'done').sort(byCompletedLatest),
    };
  }, [tasks, today]);

  const uploadFile = useCallback(
    async (taskId, file) => {
      await api.uploadFile(taskId, file);
      // On AWS the indexer runs just after the upload, so the link can take a moment to appear.
      for (let attempt = 0; attempt < 5; attempt += 1) {
        const latest = await refreshTasks();
        if (latest.find((t) => t.taskId === taskId)?.attachmentKey) return;
        await wait(1000);
      }
    },
    [api, refreshTasks],
  );

  const shared = { newIds, api, onChanged: refresh, onUpload: uploadFile };

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="brand">TaskCloud</h1>
        <p className="today-line">{formatLongDay(today)}</p>
        {localMode ? <span className="hint">Local mode</span> : <button type="button" className="link" onClick={onSignOut}>Log out</button>}
      </header>

      <div className="layout">
        <main className="notebook">
          <PlannerBox
            api={api}
            onPlanned={async (planned) => {
              setNewIds(new Set(planned.map((t) => t.taskId)));
              await refresh();
            }}
          />

          <section className="add-task" aria-label="Add a task">
            <TaskForm
              submitLabel="Add task"
              onSubmit={async (fields) => {
                await api.createTask(fields);
                await refresh();
              }}
            />
          </section>

          {loadError && (
            <div className="load-error" role="alert">
              <p className="error">{loadError}</p>
              {localMode && <p className="hint">Is the local server running? Start it with <code>python local/server.py</code>.</p>}
              <button type="button" onClick={load}>Try again</button>
            </div>
          )}
          {!tasks && !loadError && <p className="empty" role="status">Loading your tasks…</p>}
          {tasks && (
            <>
              <TaskSection title="Today" tasks={dueNow} emptyText="Nothing due today. Add a task above, or ask the planner." {...shared} />
              <TaskSection title="Upcoming" tasks={upcoming} emptyText="No tasks coming up. Tell the planner about your next deadline." {...shared} />
              <TaskSection title="Done" tasks={done} emptyText="Tick off a task and it moves here, and counts toward your streak." {...shared} />
            </>
          )}
        </main>
        <ProgressPanel progress={progress} error={progressError} />
      </div>
    </div>
  );
}
