const ANY_TIME = [
  'You can do it!', 'Sip some water?', 'One tiny task?', 'I believe in you!', 'Nice posture!', 'Snack break soon?',
  'Tap me to plan!', 'Let\'s tick a box!', 'Stretch your arms!', 'You\'re doing great.', 'Mochi is cheering!',
  'Small steps count.', 'Deep breath in...', 'Keep going, friend!', 'So proud of you.', 'Pencils ready?',
];
const BY_TIME = {
  morning: ['Good morning!', 'Fresh page today!', 'Breakfast first?', 'Sun\'s up, let\'s go!'],
  afternoon: ['Afternoon power!', 'Halfway there!', 'Lunch was yummy?', 'Time for one more?'],
  evening: ['Cosy study time.', 'Almost done today!', 'Tea and notes?', 'Evening, friend!'],
  night: ['It\'s getting late...', 'Sleep helps memory!', 'Bedtime soon?', 'Sleepy... zzz'],
};

const pick = (items) => items[Math.floor(Math.random() * items.length)];

export function timeOfDay(hour) {
  if (hour < 5 || hour >= 22) return 'night';
  if (hour < 12) return 'morning';
  if (hour < 17) return 'afternoon';
  return 'evening';
}

export function randomPhrase({ hour, overdue = 0, dueToday = 0 }) {
  const period = timeOfDay(hour);
  const roll = Math.random();
  if (overdue > 0 && roll < 0.2) {
    return { text: overdue === 1 ? 'One task is waiting!' : `${overdue} tasks are waiting!`, mood: 'worried' };
  }
  if (dueToday > 0 && roll < 0.35) {
    return { text: dueToday === 1 ? 'One left for today!' : `${dueToday} to go today!`, mood: 'happy' };
  }
  if (roll < 0.6) return { text: pick(BY_TIME[period]), mood: period === 'night' ? 'sleepy' : 'happy' };
  return { text: pick(ANY_TIME), mood: 'happy' };
}

const CHEERS = ['Yay! Well done!', 'Tick! So good!', 'You did it!', 'Woohoo!', 'One less to do!', 'Sparkly work!'];
export const randomCheer = () => pick(CHEERS);
