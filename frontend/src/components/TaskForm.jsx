import { useId, useState } from 'react';
import { todayIst } from '../dates.js';

// Used both for adding a task and for editing one in place.
export default function TaskForm({ initial, defaultDate, submitLabel, onSubmit, onCancel }) {
  const id = useId();
  const blank = { title: '', dueDate: defaultDate ?? todayIst(), priority: 'medium', estMinutes: 30 };
  const [fields, setFields] = useState(initial ?? blank);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const set = (name) => (event) => setFields({ ...fields, [name]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await onSubmit({
        title: fields.title,
        dueDate: fields.dueDate,
        priority: fields.priority,
        estMinutes: Number(fields.estMinutes),
      });
      if (!initial) setFields({ ...blank, dueDate: fields.dueDate });
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="task-form" onSubmit={submit}>
      <label className="field-title" htmlFor={`${id}-title`}>Task</label>
      <input
        id={`${id}-title`}
        className="input-title"
        required
        maxLength={120}
        placeholder="Finish lab record"
        value={fields.title}
        onChange={set('title')}
      />
      <div className="field">
        <label htmlFor={`${id}-due`}>Due</label>
        <input id={`${id}-due`} type="date" required value={fields.dueDate} onChange={set('dueDate')} />
      </div>
      <div className="field">
        <label htmlFor={`${id}-priority`}>Priority</label>
        <select id={`${id}-priority`} value={fields.priority} onChange={set('priority')}>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
      </div>
      <div className="field field-minutes">
        <label htmlFor={`${id}-minutes`}>Minutes</label>
        <input id={`${id}-minutes`} type="number" required min={5} max={480} step={5} value={fields.estMinutes} onChange={set('estMinutes')} />
      </div>
      <div className="form-actions">
        <button className="primary" type="submit" disabled={busy}>{busy ? 'Saving…' : submitLabel}</button>
        {onCancel && <button type="button" onClick={onCancel}>Cancel</button>}
      </div>
      {error && <p className="error form-error" role="alert">{error}</p>}
    </form>
  );
}
