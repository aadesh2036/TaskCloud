import { useRef, useState } from 'react';
import { formatDay, istDateOf, todayIst } from '../dates.js';
import TaskForm from './TaskForm.jsx';

const PRIORITY_LABEL = { low: 'Low', medium: 'Medium', high: 'High' };

function dateChip(task) {
  if (task.status === 'done') {
    return { text: task.completedAt ? `Done ${formatDay(istDateOf(task.completedAt))}` : 'Done' };
  }
  const today = todayIst();
  if (task.dueDate === today) return { text: 'Today' };
  if (task.dueDate < today) return { text: `${formatDay(task.dueDate)}, overdue`, late: true };
  return { text: formatDay(task.dueDate) };
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const LEAVE_MS = 220;

export default function TaskItem({ task, isNew, order = 0, api, onChanged, onUpload, onCompleted }) {
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  // Shows the tick straight away, rather than snapping back until the API replies.
  const [pendingDone, setPendingDone] = useState(null);
  const [leaving, setLeaving] = useState(false);
  const fileInput = useRef(null);
  const checkbox = useRef(null);
  const done = task.status === 'done';
  const chip = dateChip(task);

  async function run(label, action) {
    setBusy(label);
    setError('');
    try {
      await action();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy('');
    }
  }

  const toggleDone = () => {
    setPendingDone(!done);
    run('saving', async () => {
      try {
        await api.updateTask(task.taskId, { status: done ? 'todo' : 'done' });
        if (!done) onCompleted?.(checkbox.current?.getBoundingClientRect());
        await onChanged();
      } finally {
        setPendingDone(null);
      }
    });
  };

  const remove = () => {
    if (!window.confirm(`Delete "${task.title}"${task.attachmentKey ? ' and its attached file' : ''}?`)) return;
    run('deleting', async () => {
      await api.deleteTask(task.taskId);
      setLeaving(true);
      await wait(LEAVE_MS);
      await onChanged();
    });
  };

  const upload = (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (file) run('uploading', () => onUpload(task.taskId, file));
  };

  const openFile = () => {
    // Opened before the await, because browsers block pop-ups opened after one.
    const tab = window.open('', '_blank');
    run('opening', async () => {
      try {
        const { url } = await api.getDownloadUrl(task.taskId);
        if (tab) {
          tab.opener = null;
          tab.location.href = url;
        } else {
          window.location.href = url;
        }
      } catch (caught) {
        tab?.close();
        throw caught;
      }
    });
  };

  if (editing) {
    return (
      <li className="task editing">
        <TaskForm
          initial={{ title: task.title, dueDate: task.dueDate, priority: task.priority, estMinutes: task.estMinutes }}
          submitLabel="Save changes"
          onCancel={() => setEditing(false)}
          onSubmit={async (fields) => {
            await api.updateTask(task.taskId, fields);
            await onChanged();
            setEditing(false);
          }}
        />
      </li>
    );
  }

  return (
    <li
      className={`task priority-${task.priority}${done ? ' is-done' : ''}${isNew ? ' is-new' : ''}${leaving ? ' is-leaving' : ''}`}
      style={{ '--order': Math.min(order, 8) }}
    >
      <div className="task-line">
        <input
          ref={checkbox}
          type="checkbox"
          id={`done-${task.taskId}`}
          checked={pendingDone ?? done}
          disabled={Boolean(busy)}
          onChange={toggleDone}
        />
        <label className="task-title" htmlFor={`done-${task.taskId}`}><span className="task-title-text">{task.title}</span></label>
        {task.source === 'agent' && <span className="ai-badge" title="Created by the AI planner">AI</span>}
      </div>
      <div className="task-meta">
        <span className={`date-chip${chip.late ? ' is-late' : ''}`}>{chip.text}</span>
        <span className="priority-chip">{PRIORITY_LABEL[task.priority]}</span>
        <span>{task.estMinutes} min</span>
        <span className="task-actions">
          {task.attachmentKey ? (
            <button type="button" className="link" onClick={openFile} disabled={Boolean(busy)}>
              Open {task.attachmentKey.split('/').pop()}
            </button>
          ) : (
            <>
              <input ref={fileInput} type="file" className="visually-hidden" tabIndex={-1} aria-hidden="true" onChange={upload} />
              <button type="button" className="link" onClick={() => fileInput.current?.click()} disabled={Boolean(busy)}>
                {busy === 'uploading' ? 'Attaching…' : 'Attach file'}
              </button>
            </>
          )}
          {!done && (
            <button type="button" className="link" onClick={() => setEditing(true)} disabled={Boolean(busy)} aria-label={`Edit ${task.title}`}>
              Edit
            </button>
          )}
          <button type="button" className="link" onClick={remove} disabled={Boolean(busy)} aria-label={`Delete ${task.title}`}>
            Delete
          </button>
        </span>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
    </li>
  );
}
