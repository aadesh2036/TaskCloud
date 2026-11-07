import TaskItem from './TaskItem.jsx';

const WASHI = { Today: 'washi-pink', Upcoming: 'washi-lilac', Done: 'washi-mint' };

export default function TaskSection({ title, tasks, emptyText, shared }) {
  const headingId = `section-${title.toLowerCase()}`;
  return (
    <section aria-labelledby={headingId} className="task-section">
      <h2 id={headingId} className={`washi-heading ${WASHI[title]}`}>
        {title} <span className="count">{tasks.length}</span>
      </h2>
      {tasks.length === 0 ? (
        <p className="empty">{emptyText}</p>
      ) : (
        <ul className="task-list">
          {tasks.map((task, index) => (
            <TaskItem key={task.taskId} task={task} order={index} isNew={shared.newIds.has(task.taskId)} {...shared} />
          ))}
        </ul>
      )}
    </section>
  );
}
