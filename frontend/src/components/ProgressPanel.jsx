import { useState } from 'react';
import { formatDay, weekdayLetter } from '../dates.js';

const WIDTH = 280;
const HEIGHT = 130;
const BASELINE = 104;
const TOP = 12;
const SLOT = WIDTH / 7;
const BAR = 22;
const RADIUS = 42;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const MAX_STARS = 7;

function barPath(x, y, width, bottom) {
  // Rounded only at the data end, so every bar still sits squarely on the baseline.
  const radius = Math.min(6, bottom - y);
  return `M${x},${bottom} V${y + radius} Q${x},${y} ${x + radius},${y} H${x + width - radius} Q${x + width},${y} ${x + width},${y + radius} V${bottom} Z`;
}

function WeekChart({ days }) {
  const [active, setActive] = useState(null);
  const max = Math.max(1, ...days.map((d) => d.done));
  const shown = active ?? days.length - 1;
  const summary = `${formatDay(days[shown].date)}: ${days[shown].done} completed`;

  return (
    <figure className="chart">
      <figcaption>Tasks completed, last 7 days</figcaption>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="group" aria-label="Bar chart of tasks completed per day. Focus a bar to hear its value.">
        <line x1="0" x2={WIDTH} y1={BASELINE} y2={BASELINE} className="chart-baseline" />
        {days.map((day, index) => {
          const height = day.done ? Math.max(6, (day.done / max) * (BASELINE - TOP)) : 0;
          const x = index * SLOT + (SLOT - BAR) / 2;
          const isToday = index === days.length - 1;
          return (
            <g
              key={day.date}
              tabIndex={0}
              role="img"
              aria-label={`${formatDay(day.date)}: ${day.done} completed`}
              className={`chart-day${shown === index ? ' is-active' : ''}`}
              onMouseEnter={() => setActive(index)}
              onMouseLeave={() => setActive(null)}
              onFocus={() => setActive(index)}
              onBlur={() => setActive(null)}
            >
              {/* Full-height hit target, so a zero-value day can still be hovered. */}
              <rect x={index * SLOT} y={0} width={SLOT} height={HEIGHT} fill="transparent" />
              {height > 0 && (
                <path d={barPath(x, BASELINE - height, BAR, BASELINE)} className="chart-bar" style={{ animationDelay: `${index * 45}ms` }} />
              )}
              <text x={x + BAR / 2} y={HEIGHT - 8} textAnchor="middle" className={`chart-label${isToday ? ' is-today' : ''}`}>
                {weekdayLetter(day.date)}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="chart-readout" aria-live="polite">{summary}</p>
      <table className="visually-hidden">
        <caption>Tasks completed per day</caption>
        <thead><tr><th scope="col">Day</th><th scope="col">Completed</th></tr></thead>
        <tbody>
          {days.map((day) => <tr key={day.date}><td>{formatDay(day.date)}</td><td>{day.done}</td></tr>)}
        </tbody>
      </table>
    </figure>
  );
}

export default function ProgressPanel({ progress, error, dueToday }) {
  const shell = (children, busy) => (
    <aside className="panel progress" aria-label="Progress" aria-busy={busy || undefined}>
      <span className="tape tape-peri" aria-hidden="true" />
      <h2 className="panel-heading">Progress</h2>
      {children}
    </aside>
  );
  if (error && !progress) return shell(<p className="error" role="alert">{error}</p>);
  if (!progress) return shell(<p className="empty" role="status">Counting your ticks…</p>, true);

  const planned = progress.completedToday + dueToday;
  const share = planned ? progress.completedToday / planned : 0;
  const days = progress.streakDays === 1 ? 'day' : 'days';
  const stars = Math.min(progress.streakDays, MAX_STARS);

  return shell(
    <>
      <div className="today-ring">
        <div className="ring">
          <svg viewBox="0 0 100 100" aria-hidden="true" focusable="false">
            <circle className="ring-track" cx="50" cy="50" r={RADIUS} />
            <circle
              className="ring-value"
              cx="50"
              cy="50"
              r={RADIUS}
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={CIRCUMFERENCE * (1 - share)}
            />
          </svg>
          <span className="ring-label">{progress.completedToday}/{planned}</span>
        </div>
        <div>
          <p className="ring-caption">{planned === 0 ? 'Nothing planned today' : share === 1 ? 'All done today!' : 'Done today'}</p>
          <p className="streak"><strong>{progress.streakDays}</strong> {days} in a row</p>
          {stars > 0 && <p className="stars" aria-hidden="true">{Array.from({ length: stars }, (_, i) => <span key={i} style={{ animationDelay: `${i * 70}ms` }}>★</span>)}</p>}
        </div>
      </div>
      <dl className="counts">
        <div><dt>To do</dt><dd>{progress.todo}</dd></div>
        <div><dt>Done</dt><dd>{progress.done}</dd></div>
        <div><dt>Total</dt><dd>{progress.total}</dd></div>
      </dl>
      <WeekChart days={progress.last7Days} />
    </>,
  );
}
