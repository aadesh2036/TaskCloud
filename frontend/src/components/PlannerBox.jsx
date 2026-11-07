import { useState } from 'react';

const MAX = 1000;

export default function PlannerBox({ api, onPlanned }) {
  const [prompt, setPrompt] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
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
    }
  }

  return (
    <section className="planner" aria-labelledby="planner-heading">
      <h2 id="planner-heading" className="planner-heading"><span>Plan with AI</span></h2>
      <form onSubmit={submit}>
        <label htmlFor="planner-prompt">Describe what you need to get done. The planner adds the tasks for you.</label>
        <textarea
          id="planner-prompt"
          rows={2}
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
          <span className="hint">{prompt.length} of {MAX} characters</span>
        </div>
      </form>
      <div aria-live="polite">
        {busy && <p className="hint">This can take up to 20 seconds.</p>}
        {result && (
          <div className="plan-result">
            <p>{result.summary}</p>
            <p className="hint">
              Added {result.tasks.length} {result.tasks.length === 1 ? 'task' : 'tasks'}, marked with <span className="ai-badge">AI</span> below.
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
