import TaskItem from './TaskItem.jsx';

export default function TaskSection({ title, tasks, emptyText, newIds, api, onChanged, onUpload }) {
  const headingId = `section-${title.toLowerCase()}`;
  return (
    <section aria-labelledby={headingId} className="task-section">
      <h2 id={headingId} className="section-heading">
        {title} <span className="count">{tasks.length}</span>
      </h2>
      {tasks.length === 0 ? (
        <p className="empty">{emptyText}</p>
      ) : (
        <ul className="task-list">
          {tasks.map((task) => (
            <TaskItem
              key={task.taskId}
              task={task}
              isNew={newIds.has(task.taskId)}
              api={api}
              onChanged={onChanged}
              onUpload={onUpload}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
