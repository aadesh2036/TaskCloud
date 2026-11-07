import { useMemo, useRef, useState } from 'react';
import { formatLongDay, formatMonth, monthGrid } from '../dates.js';
import AddTask from './AddTask.jsx';
import TaskItem from './TaskItem.jsx';

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MAX_CHIPS = 2;
const SWIPE_PX = 50;

export default function CalendarView({ tasks, today, shared, onAdd }) {
  const [year, setYear] = useState(Number(today.slice(0, 4)));
  const [month, setMonth] = useState(Number(today.slice(5, 7)) - 1);
  const [selected, setSelected] = useState(today);
  const [direction, setDirection] = useState('next');

  const byDate = useMemo(() => {
    const map = new Map();
    for (const task of tasks) {
      if (!map.has(task.dueDate)) map.set(task.dueDate, []);
      map.get(task.dueDate).push(task);
    }
    return map;
  }, [tasks]);

  function move(step) {
    const moved = new Date(Date.UTC(year, month + step, 1));
    setDirection(step > 0 ? 'next' : 'prev');
    setYear(moved.getUTCFullYear());
    setMonth(moved.getUTCMonth());
  }

  // A swipe must be mostly sideways, so scrolling the page never changes the month.
  const touchStart = useRef(null);
  function onTouchStart(event) {
    const touch = event.touches[0];
    touchStart.current = { x: touch.clientX, y: touch.clientY };
  }
  function onTouchEnd(event) {
    if (!touchStart.current) return;
    const touch = event.changedTouches[0];
    const dx = touch.clientX - touchStart.current.x;
    const dy = touch.clientY - touchStart.current.y;
    touchStart.current = null;
    if (Math.abs(dx) >= SWIPE_PX && Math.abs(dx) > Math.abs(dy) * 1.5) move(dx < 0 ? 1 : -1);
  }

  function goToday() {
    setYear(Number(today.slice(0, 4)));
    setMonth(Number(today.slice(5, 7)) - 1);
    setSelected(today);
  }

  const cells = monthGrid(year, month);
  const monthPrefix = `${year}-${String(month + 1).padStart(2, '0')}`;
  const selectedTasks = byDate.get(selected) ?? [];

  return (
    <div className="calendar">
      <div className="calendar-head">
        <button type="button" className="icon-button" onClick={() => move(-1)} aria-label="Previous month">‹</button>
        <h2 aria-live="polite">{formatMonth(year, month)}</h2>
        <button type="button" className="icon-button" onClick={() => move(1)} aria-label="Next month">›</button>
        <button type="button" className="chip" onClick={goToday}>Today</button>
      </div>

      <div className="calendar-weekdays" aria-hidden="true">
        {WEEKDAYS.map((day) => <span key={day}>{day}</span>)}
      </div>
      <div key={monthPrefix} className={`calendar-grid slide-${direction}`} onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
        {cells.map((date) => {
          const dayTasks = byDate.get(date) ?? [];
          const open = dayTasks.filter((t) => t.status === 'todo');
          const allDone = dayTasks.length > 0 && open.length === 0;
          const late = date < today && open.length > 0;
          const classes = [
            'day',
            date.startsWith(monthPrefix) ? '' : 'is-other',
            date === today ? 'is-today' : '',
            date === selected ? 'is-selected' : '',
            late ? 'is-late' : '',
          ].filter(Boolean).join(' ');
          const taskWord = dayTasks.length === 1 ? 'task' : 'tasks';
          const label = `${formatLongDay(date)}: ${dayTasks.length} ${taskWord}${late ? ', overdue' : ''}${allDone ? ', all done' : ''}`;
          return (
            <button key={date} type="button" className={classes} aria-label={label} aria-pressed={date === selected} onClick={() => setSelected(date)}>
              <span className="day-number">{Number(date.slice(8))}</span>
              {allDone && <span className="day-stamp" aria-hidden="true">★</span>}
              <span className="day-chips" aria-hidden="true">
                {dayTasks.slice(0, MAX_CHIPS).map((task) => (
                  <span key={task.taskId} className={`day-chip priority-${task.priority}${task.status === 'done' ? ' is-done' : ''}`}>{task.title}</span>
                ))}
                {dayTasks.length > MAX_CHIPS && <span className="day-more">+{dayTasks.length - MAX_CHIPS}</span>}
              </span>
              <span className="day-dots" aria-hidden="true">
                {dayTasks.slice(0, 4).map((task) => <span key={task.taskId} className={`day-dot priority-${task.priority}`} />)}
              </span>
            </button>
          );
        })}
      </div>

      <section className="day-panel" aria-labelledby="day-heading">
        <h3 id="day-heading" className="washi-heading washi-sky">{selected === today ? 'Today' : formatLongDay(selected)} <span className="count">{selectedTasks.length}</span></h3>
        {selectedTasks.length === 0 ? (
          <p className="empty">A free day! Add something, or enjoy the break.</p>
        ) : (
          <ul className="task-list">
            {selectedTasks.map((task) => <TaskItem key={task.taskId} task={task} isNew={shared.newIds.has(task.taskId)} {...shared} />)}
          </ul>
        )}
        <AddTask defaultDate={selected} onAdd={onAdd} />
      </section>
    </div>
  );
}
