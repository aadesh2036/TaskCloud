import { useEffect, useRef, useState } from 'react';
import MochiFace from './MochiFace.jsx';

const MAX = 1000;

// Stays mounted while closed, so a plan in progress and its result are not lost.
export default function PlannerBox({ api, open, onClose, onBusyChange, onPlanned }) {
  const [prompt, setPrompt] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const input = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    input.current?.focus();
    const onKey = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    onBusyChange(true);
    setError('');
    setResult(null);
    try {
      const plan = await api.plan(prompt.trim());
      setResult(plan);
      setPrompt('');
      await onPlanned(plan.tasks);
    } catch (caught) {
      setError(caught.status === 503 || caught.status === 429
        ? 'The planner is busy. Wait a few seconds and try again.'
        : caught.message);
    } finally {
      setBusy(false);
      onBusyChange(false);
    }
  }

  return (
    <section id="planner-bubble" className={`planner-bubble${open ? ' is-open' : ''}`} role="dialog" aria-labelledby="planner-heading">
      <div className="planner-head">
        <span className="planner-face"><MochiFace mood={busy ? 'thinking' : 'happy'} /></span>
        <h2 id="planner-heading">Plan with AI</h2>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close the AI planner">×</button>
      </div>
      <form onSubmit={submit}>
        <label htmlFor="planner-prompt">Tell Mochi what you need to get done, and your tasks get added for you.</label>
        <textarea
          id="planner-prompt"
          ref={input}
          rows={3}
          required
          maxLength={MAX}
          placeholder="DBMS exam on Friday, finish my lab record, and revise two hours a day."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        <div className="planner-row">
          <button className="ai-button" type="submit" disabled={busy || !prompt.trim()}>
            {busy ? 'Planning…' : 'Make my plan'}
          </button>
          <span className="hint">{prompt.length} of {MAX}</span>
        </div>
      </form>
      <div aria-live="polite">
        {busy && <p className="hint planner-wait">This can take up to 20 seconds.</p>}
        {result && (
          <div className="plan-result">
            <p>{result.summary}</p>
            <p className="hint">
              Added {result.tasks.length} {result.tasks.length === 1 ? 'task' : 'tasks'}, marked with <span className="ai-badge">AI</span>.
            </p>
            {result.rejected.length > 0 && (
              <details>
                <summary>{result.rejected.length} not added</summary>
                <ul>
                  {result.rejected.map((item, index) => (
                    <li key={index}>{item.title || 'Untitled'}: {item.reason}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
      </div>
      {error && <p className="error" role="alert">{error}</p>}
    </section>
  );
}
