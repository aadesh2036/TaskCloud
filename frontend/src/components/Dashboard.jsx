import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { randomCheer } from '../data/phrases.js';
import { todayIst } from '../dates.js';
import AddTask from './AddTask.jsx';
import CalendarView from './CalendarView.jsx';
import Confetti, { makeBurst } from './Confetti.jsx';
import FocusTimer from './FocusTimer.jsx';
import Mascot from './Mascot.jsx';
import PlannerBox from './PlannerBox.jsx';
import ProgressPanel from './ProgressPanel.jsx';
import QuoteCard from './QuoteCard.jsx';
import TaskSection from './TaskSection.jsx';

const PRIORITY_ORDER = { high: 0, medium: 1, low: 2 };
const byDueDate = (a, b) => a.dueDate.localeCompare(b.dueDate) || PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority];
const byCompletedLatest = (a, b) => (b.completedAt ?? '').localeCompare(a.completedAt ?? '');
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const FILTERS = [
  { id: 'all', label: 'All', test: () => true },
  { id: 'high', label: 'High priority', test: (t) => t.priority === 'high' },
  { id: 'ai', label: 'From AI', test: (t) => t.source === 'agent' },
  { id: 'file', label: 'With a file', test: (t) => Boolean(t.attachmentKey) },
];
const VIEW_KEY = 'taskcloud-view';

function savedView() {
  try {
    return localStorage.getItem(VIEW_KEY) === 'calendar' ? 'calendar' : 'list';
  } catch {
    return 'list';
  }
}

const prefersReducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

export default function Dashboard({ api, localMode, onSignOut }) {
  const [tasks, setTasks] = useState(null);
  const [progress, setProgress] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [progressError, setProgressError] = useState('');
  const [newIds, setNewIds] = useState(new Set());
  const [view, setView] = useState(savedView);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [plannerOpen, setPlannerOpen] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [mascotEvent, setMascotEvent] = useState(null);
  const [bursts, setBursts] = useState([]);
  const mascotButton = useRef(null);
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

  const { dueNow, upcoming, done, overdue, visibleCount } = useMemo(() => {
    const all = tasks ?? [];
    const query = search.trim().toLowerCase();
    const test = FILTERS.find((item) => item.id === filter).test;
    const visible = all.filter((t) => test(t) && (!query || t.title.toLowerCase().includes(query)));
    const open = visible.filter((t) => t.status === 'todo').sort(byDueDate);
    return {
      dueNow: open.filter((t) => t.dueDate <= today),
      upcoming: open.filter((t) => t.dueDate > today),
      done: visible.filter((t) => t.status === 'done').sort(byCompletedLatest),
      overdue: all.filter((t) => t.status === 'todo' && t.dueDate < today).length,
      visibleCount: visible.length,
    };
  }, [tasks, today, filter, search]);

  const dueToday = useMemo(() => (tasks ?? []).filter((t) => t.status === 'todo' && t.dueDate <= today).length, [tasks, today]);
  const filtering = filter !== 'all' || search.trim() !== '';

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

  const celebrate = useCallback((rect) => {
    setMascotEvent({ text: randomCheer(), mood: 'cheer' });
    if (!rect || prefersReducedMotion()) return;
    const burst = makeBurst(rect.left + rect.width / 2, rect.top + rect.height / 2);
    setBursts((current) => [...current, burst]);
    setTimeout(() => setBursts((current) => current.filter((item) => item.id !== burst.id)), 1000);
  }, []);

  const addTask = useCallback(
    async (fields) => {
      const created = await api.createTask(fields);
      setNewIds(new Set([created.taskId]));
      await refresh();
    },
    [api, refresh],
  );

  const closePlanner = useCallback(() => {
    setPlannerOpen(false);
    mascotButton.current?.focus();
  }, []);

  const onPlanned = useCallback(
    async (planned) => {
      setNewIds(new Set(planned.map((t) => t.taskId)));
      await refresh();
      setMascotEvent(
        planned.length
          ? { text: `${planned.length} new ${planned.length === 1 ? 'task' : 'tasks'} added!`, mood: 'cheer' }
          : { text: 'Tell me a bit more?', mood: 'worried' },
      );
    },
    [refresh],
  );

  const onTimerFinish = useCallback((mode) => {
    setMascotEvent(mode === 'focus' ? { text: 'Focus done! Rest now.', mood: 'cheer' } : { text: 'Ready to go again?', mood: 'happy' });
  }, []);

  function chooseView(next) {
    setView(next);
    try {
      localStorage.setItem(VIEW_KEY, next);
    } catch {
      // Remembering the view is only a convenience, so a blocked browser store is fine.
    }
  }

  const shared = { newIds, api, onChanged: refresh, onUpload: uploadFile, onCompleted: celebrate };

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="brand">TaskCloud</h1>
        {localMode ? <span className="hint">Local mode</span> : <button type="button" className="link" onClick={onSignOut}>Log out</button>}
      </header>

      <QuoteCard today={today} />

      <div className="layout">
        <main className="journal">
          <div className="toolbar">
            <div className="view-switch" role="group" aria-label="Choose a view">
              <button type="button" aria-pressed={view === 'list'} onClick={() => chooseView('list')}>List</button>
              <button type="button" aria-pressed={view === 'calendar'} onClick={() => chooseView('calendar')}>Calendar</button>
              <span className={`view-thumb is-${view}`} aria-hidden="true" />
            </div>
            {view === 'list' && <AddTask onAdd={addTask} />}
          </div>

          {loadError && (
            <div className="load-error" role="alert">
              <p className="error">{loadError}</p>
              {localMode && <p className="hint">Is the local server running? Start it with <code>python local/server.py</code>.</p>}
              <button type="button" onClick={load}>Try again</button>
            </div>
          )}
          {!tasks && !loadError && <p className="empty" role="status">Finding your tasks…</p>}

          {tasks && view === 'list' && (
            <div className="view-pane" key="list">
              <div className="filters">
                <div role="group" aria-label="Filter tasks" className="filter-chips">
                  {FILTERS.map((item) => (
                    <button key={item.id} type="button" className="chip" aria-pressed={filter === item.id} onClick={() => setFilter(item.id)}>
                      {item.label}
                    </button>
                  ))}
                </div>
                <label className="search">
                  <span className="visually-hidden">Search tasks</span>
                  <input type="search" placeholder="Search tasks" value={search} onChange={(e) => setSearch(e.target.value)} />
                </label>
              </div>
              {filtering && visibleCount === 0 ? (
                <p className="empty">No tasks match. Try another filter or search.</p>
              ) : (
                <>
                  <TaskSection title="Today" tasks={dueNow} emptyText="Nothing due today. Add a task, or tap Mochi to plan." shared={shared} />
                  <TaskSection title="Upcoming" tasks={upcoming} emptyText="No tasks coming up. Tell Mochi about your next deadline." shared={shared} />
                  <TaskSection title="Done" tasks={done} emptyText="Tick off a task and it lands here, and counts toward your streak." shared={shared} />
                </>
              )}
            </div>
          )}
          {tasks && view === 'calendar' && (
            <div className="view-pane" key="calendar">
              <CalendarView tasks={tasks} today={today} shared={shared} onAdd={addTask} />
            </div>
          )}
        </main>

        <div className="sidebar">
          <ProgressPanel progress={progress} error={progressError} dueToday={dueToday} />
          <FocusTimer onFinish={onTimerFinish} />
        </div>
      </div>

      <PlannerBox api={api} open={plannerOpen} onClose={closePlanner} onBusyChange={setPlanning} onPlanned={onPlanned} />
      <Mascot
        ref={mascotButton}
        event={mascotEvent}
        busy={planning}
        open={plannerOpen}
        overdue={overdue}
        dueToday={dueToday}
        onToggle={() => setPlannerOpen((value) => !value)}
      />
      <Confetti bursts={bursts} />
    </div>
  );
}
