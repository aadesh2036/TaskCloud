// The mascot's face. Purely decorative, so whatever wraps it provides any label.
export default function MochiFace({ mood = 'happy' }) {
  return (
    <svg className={`mochi-face mood-${mood}`} viewBox="0 0 100 100" aria-hidden="true" focusable="false">
      <circle className="mochi-body" cx="50" cy="50" r="46" />
      <ellipse className="mochi-blush" cx="21" cy="62" rx="10" ry="6.5" />
      <ellipse className="mochi-blush" cx="79" cy="62" rx="10" ry="6.5" />

      {mood === 'cheer' && (
        <g className="mochi-line">
          <path d="M26 50q8-11 16 0" />
          <path d="M58 50q8-11 16 0" />
        </g>
      )}
      {mood === 'sleepy' && (
        <g className="mochi-line">
          <path d="M26 47q8 7 16 0" />
          <path d="M58 47q8 7 16 0" />
        </g>
      )}
      {(mood === 'happy' || mood === 'thinking' || mood === 'worried') && (
        <g className="mochi-eyes">
          <g className="mochi-eye">
            <ellipse cx="34" cy="46" rx="6" ry="7.5" />
            <circle className="mochi-glint" cx="36" cy="43" r="2.2" />
          </g>
          <g className="mochi-eye">
            <ellipse cx="66" cy="46" rx="6" ry="7.5" />
            <circle className="mochi-glint" cx="68" cy="43" r="2.2" />
          </g>
        </g>
      )}

      {mood === 'happy' && <path className="mochi-line" d="M43 61q7 7 14 0" />}
      {mood === 'cheer' && <path className="mochi-mouth" d="M40 59h20q-1 14-10 14t-10-14z" />}
      {mood === 'sleepy' && <circle className="mochi-line" cx="50" cy="64" r="3.5" />}
      {mood === 'thinking' && <path className="mochi-line" d="M44 65q6-5 12 0" />}
      {mood === 'worried' && <path className="mochi-line" d="M43 67q7-7 14 0" />}
    </svg>
  );
}
