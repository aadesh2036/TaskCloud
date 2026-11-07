// All dates follow IST, matching the backend's progress and streak calculations.
const istDate = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' });

export const todayIst = () => istDate.format(new Date());

export const istDateOf = (timestamp) => istDate.format(new Date(timestamp));

function utc(isoDate) {
  return new Date(`${isoDate}T00:00:00Z`);
}

// timeZone UTC here because a plain YYYY-MM-DD has no zone. Anything else could shift the day.
export function formatDay(isoDate) {
  return utc(isoDate).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' });
}

export function formatLongDay(isoDate) {
  return utc(isoDate).toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' });
}

export function weekdayLetter(isoDate) {
  return utc(isoDate).toLocaleDateString('en-IN', { weekday: 'short', timeZone: 'UTC' });
}
