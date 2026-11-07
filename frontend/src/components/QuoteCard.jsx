import { quoteForDate } from '../data/quotes.js';
import { formatLongDay } from '../dates.js';

export default function QuoteCard({ today }) {
  return (
    <figure className="quote-card">
      <span className="tape tape-blue" aria-hidden="true" />
      <figcaption>Today's little note, {formatLongDay(today)}</figcaption>
      <blockquote>{quoteForDate(today)}</blockquote>
    </figure>
  );
}
