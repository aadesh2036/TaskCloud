import { useEffect, useState } from 'react';

const MODES = [
  { id: 'focus', label: 'Focus', minutes: 25 },
  { id: 'rest', label: 'Rest', minutes: 5 },
];
const RADIUS = 46;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

const clock = (seconds) => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;

export default function FocusTimer({ onFinish }) {
  const [mode, setMode] = useState(MODES[0]);
  const [remaining, setRemaining] = useState(MODES[0].minutes * 60);
  const [endsAt, setEndsAt] = useState(null);

  useEffect(() => {
    if (!endsAt) return undefined;
    const original = document.title;
    // Worked out from the clock, because browsers slow down timers in background tabs.
    const tick = () => {
      const left = Math.max(0, Math.round((endsAt - Date.now()) / 1000));
      setRemaining(left);
      document.title = `${clock(left)} ${mode.label}`;
      if (left === 0) {
        setEndsAt(null);
        onFinish(mode.id);
      }
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => {
      clearInterval(interval);
      document.title = original;
    };
  }, [endsAt, mode, onFinish]);

  function choose(next) {
    setEndsAt(null);
    setMode(next);
    setRemaining(next.minutes * 60);
  }

  const total = mode.minutes * 60;
  const start = () => setEndsAt(Date.now() + (remaining || total) * 1000);
  const pause = () => setEndsAt(null);
  const reset = () => choose(mode);

  return (
    <section className="panel focus-timer" aria-labelledby="focus-heading">
      <span className="tape tape-mint" aria-hidden="true" />
      <h2 id="focus-heading" className="panel-heading">Focus timer</h2>
      <div className="mode-switch" role="group" aria-label="Timer length">
        {MODES.map((item) => (
          <button key={item.id} type="button" className="chip" aria-pressed={mode.id === item.id} onClick={() => choose(item)}>
            {item.label} {item.minutes}
          </button>
        ))}
      </div>
      <div className="timer-ring">
        <svg viewBox="0 0 100 100" aria-hidden="true" focusable="false">
          <circle className="ring-track" cx="50" cy="50" r={RADIUS} />
          <circle
            className="ring-value ring-mint"
            cx="50"
            cy="50"
            r={RADIUS}
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={CIRCUMFERENCE * (1 - remaining / total)}
          />
        </svg>
        <span role="timer" className="timer-digits">{clock(remaining)}</span>
      </div>
      <div className="timer-actions">
        {endsAt ? (
          <button type="button" className="primary" onClick={pause}>Pause</button>
        ) : (
          <button type="button" className="primary" onClick={start}>{remaining === total || remaining === 0 ? 'Start' : 'Resume'}</button>
        )}
        <button type="button" onClick={reset}>Reset</button>
      </div>
    </section>
  );
}
