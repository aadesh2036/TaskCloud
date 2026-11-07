import { forwardRef, useEffect, useRef, useState } from 'react';
import { randomPhrase } from '../data/phrases.js';
import { istHour } from '../dates.js';
import MochiFace from './MochiFace.jsx';

const SHOW_MS = 6000;
const QUIET_MIN_MS = 16000;
const QUIET_EXTRA_MS = 16000;

// Sits in the corner, says short random phrases, and opens the AI planner when pressed.
const Mascot = forwardRef(function Mascot({ event, busy, open, overdue, dueToday, onToggle }, ref) {
  const [speech, setSpeech] = useState(null);
  const [visible, setVisible] = useState(false);
  const [mood, setMood] = useState('happy');
  const [hop, setHop] = useState(0);
  const counts = useRef({ overdue, dueToday });
  counts.current = { overdue, dueToday };
  const hideTimer = useRef(null);

  function say(text, nextMood) {
    setSpeech(text);
    setMood(nextMood);
    setVisible(true);
    clearTimeout(hideTimer.current);
    hideTimer.current = setTimeout(() => {
      setVisible(false);
      setMood(istHour() >= 22 || istHour() < 5 ? 'sleepy' : 'happy');
    }, SHOW_MS);
  }

  useEffect(() => {
    let timer;
    const next = (delay) => {
      timer = setTimeout(() => {
        const phrase = randomPhrase({ hour: istHour(), ...counts.current });
        say(phrase.text, phrase.mood);
        next(QUIET_MIN_MS + Math.random() * QUIET_EXTRA_MS);
      }, delay);
    };
    next(1500);
    return () => {
      clearTimeout(timer);
      clearTimeout(hideTimer.current);
    };
  }, []);

  useEffect(() => {
    if (!event) return;
    say(event.text, event.mood);
    setHop((value) => value + 1);
  }, [event]);

  const shownMood = busy ? 'thinking' : mood;
  const shownSpeech = busy ? 'Hmm, planning...' : speech;

  return (
    <div className="mascot-dock">
      {/* Idle chatter would be noisy for a screen reader, so only real events are announced. */}
      <p className="visually-hidden" role="status">{event?.text ?? ''}</p>
      <p className={`speech${(visible || busy) && !open ? ' is-showing' : ''}`} aria-hidden="true">{shownSpeech}</p>
      <button
        ref={ref}
        type="button"
        className="mochi-button"
        aria-label={open ? 'Close the AI planner' : 'Plan with AI'}
        aria-expanded={open}
        aria-controls="planner-bubble"
        onClick={onToggle}
      >
        <span key={hop} className={`mochi-hop${hop ? ' is-hopping' : ''}`}>
          <span className="mochi-bob"><MochiFace mood={shownMood} /></span>
        </span>
        <span className="mochi-tag" aria-hidden="true">AI</span>
      </button>
    </div>
  );
});

export default Mascot;
