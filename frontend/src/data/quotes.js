// Written for TaskCloud, so nothing here is a misattributed "famous" quote.
export const QUOTES = [
  'Small steps still get you there.',
  'One page today beats ten pages someday.',
  'You do not have to feel ready to begin.',
  'Start messy. Tidy it later.',
  'Five focused minutes can rescue a whole evening.',
  'Progress is quiet. Keep going anyway.',
  'The hardest part of revising is opening the book.',
  'Your future self is already grateful.',
  'A slow day of work is still a day of work.',
  'Finished is lovelier than perfect.',
  'Every expert once failed this exact chapter.',
  'You have survived every hard week so far.',
  'Do the next small thing. Then the next one.',
  'Confusion is just understanding on its way.',
  'Rest is part of the plan, not a break from it.',
  'A blank page is only scary until the first line.',
  'Today is a good day to tick one box.',
  'Mistakes are how your brain takes notes.',
  'You can do hard things gently.',
  'One good hour can change how the whole day feels.',
  'Your pace is allowed to be your own.',
  'Ask the silly question. Someone else needed it too.',
  'A little every day grows into a lot.',
  'Be proud of how far this semester has carried you.',
  'Deadlines pass. What you learned stays.',
  'Drink some water. Then try that problem again.',
  'You are not behind. You are on your own page.',
  'Even tiny stars are still shining.',
  'Tomorrow will be easier because of what you do today.',
  'Close one tab. Open one book.',
  'Consistency is just kindness to your future self.',
  'A bad mark is a data point, not a verdict.',
  'Keep your pencil moving and your heart soft.',
  'You came here to learn, not to already know.',
  'Courage can look like simply sitting down to study.',
  'Big exams are made of small questions.',
  'Done today is worth two planned for tomorrow.',
  'Let today be a little better than yesterday. That is plenty.',
  'The notes you write today are a gift to exam-week you.',
  'Nobody climbs a hill by staring at the top.',
  'It is okay to start again, as many times as it takes.',
  'Your effort counts even when no one is grading it.',
  'A tidy desk is nice. A started assignment is nicer.',
  'Twenty-five minutes. You can do anything for twenty-five minutes.',
  'Hard chapters make the best stories later.',
  'You are allowed to be a beginner.',
  'Learning feels slow right up until it clicks.',
  'Take the deep breath first. The syllabus can wait a moment.',
  'What you repeat, you become good at.',
  'Celebrate the small tick marks.',
  'Sometimes showing up is the whole victory.',
  'You have more time than panic says you do.',
  'Sharp pencil, soft heart, one more page.',
  'Today only asks for today.',
  'Curiosity is a better friend than fear.',
  'The first draft only has to exist.',
  'Every finished task is a little gift to yourself.',
  'Good things grow in small, quiet hours.',
  'You are doing better than your worries claim.',
  'Stuck is a place you pass through, not where you live.',
  'A short walk can solve what an hour of staring cannot.',
  'Try once more, a little differently.',
  'Your brain is still building while you sleep. Go to bed.',
  'Slow is smooth, and smooth gets things done.',
  'Make it small enough that you cannot say no.',
  'Bravely ask for help. That is also studying.',
  'The best time to revise was last week. The next best is now.',
  'Be the classmate you would want to sit beside.',
  'One tick today. One tick tomorrow. See what happens.',
  'You can be tired and still be doing well.',
  'Every chapter ends. This one will too.',
  'Knowledge is the one thing nobody can borrow and not return.',
  'Your notebook believes in you.',
  'Comparison steals time you could spend on page twelve.',
  'Keep the promise you made to yourself this morning.',
  'Little by little is still by.',
  'Breathe in, sit down, begin.',
  'Good enough and handed in beats perfect and imaginary.',
  'You are writing your own success, one small line at a time.',
  'Today, be gentle and be stubborn.',
];

function seededShuffle(items, seed) {
  const result = [...items];
  let state = seed;
  for (let i = result.length - 1; i > 0; i -= 1) {
    // mulberry32: a small generator, so every device shuffles the same way.
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    const random = ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    const j = Math.floor(random * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

const SHUFFLED = seededShuffle(QUOTES, 20261107);

// Looks random, stays the same all day, and repeats only after the whole list has been used.
export function quoteForDate(isoDate) {
  const dayNumber = Math.floor(Date.parse(`${isoDate}T00:00:00Z`) / 86400000);
  return SHUFFLED[((dayNumber % SHUFFLED.length) + SHUFFLED.length) % SHUFFLED.length];
}
