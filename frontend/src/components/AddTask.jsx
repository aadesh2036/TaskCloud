import { useState } from 'react';
import TaskForm from './TaskForm.jsx';

// A folded form, so the page opens on the tasks rather than on empty inputs.
export default function AddTask({ defaultDate, onAdd }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="add-task">
      <button type="button" className="primary add-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className={`plus${open ? ' is-open' : ''}`} aria-hidden="true">+</span> {open ? 'Close' : 'Add a task'}
      </button>
      <div className={`fold${open ? ' is-open' : ''}`}>
        <div className="fold-inner">
          <TaskForm key={defaultDate ?? 'any'} defaultDate={defaultDate} submitLabel="Add task" onSubmit={onAdd} />
        </div>
      </div>
    </div>
  );
}
