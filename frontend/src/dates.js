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

export function istHour() {
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Kolkata', hour: 'numeric', hourCycle: 'h23' }).formatToParts(new Date());
  return Number(parts.find((part) => part.type === 'hour').value);
}

const DAY_MS = 86400000;

export function addDays(isoDate, days) {
  return new Date(utc(isoDate).getTime() + days * DAY_MS).toISOString().slice(0, 10);
}

export function formatMonth(year, month) {
  return new Date(Date.UTC(year, month, 1)).toLocaleDateString('en-IN', { month: 'long', year: 'numeric', timeZone: 'UTC' });
}

// Whole weeks, Sunday first, covering the month. month is 0 to 11.
export function monthGrid(year, month) {
  const first = new Date(Date.UTC(year, month, 1));
  const start = first.toISOString().slice(0, 10);
  const lastDay = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  const cells = Math.ceil((first.getUTCDay() + lastDay) / 7) * 7;
  return Array.from({ length: cells }, (_, index) => addDays(start, index - first.getUTCDay()));
}
