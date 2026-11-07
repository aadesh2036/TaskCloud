const SHAPES = ['★', '♥', '✿', '●'];
const COLOURS = ['#f7a8c4', '#cdb8f2', '#8fdcc0', '#ffe27a', '#9fd6f5'];
const PIECES = 12;

export function makeBurst(x, y) {
  return {
    id: `${Date.now()}-${Math.random()}`,
    x,
    y,
    pieces: Array.from({ length: PIECES }, (_, index) => {
      const angle = (index / PIECES) * Math.PI * 2 + Math.random() * 0.5;
      const distance = 45 + Math.random() * 50;
      return {
        shape: SHAPES[index % SHAPES.length],
        colour: COLOURS[index % COLOURS.length],
        dx: Math.round(Math.cos(angle) * distance),
        dy: Math.round(Math.sin(angle) * distance - 25),
        spin: Math.round(Math.random() * 300 - 150),
      };
    }),
  };
}

export default function Confetti({ bursts }) {
  return (
    <div className="confetti-layer" aria-hidden="true">
      {bursts.map((burst) => (
        <span key={burst.id} style={{ position: 'absolute', left: burst.x, top: burst.y }}>
          {burst.pieces.map((piece, index) => (
            <span
              key={index}
              className="confetti"
              style={{ '--dx': `${piece.dx}px`, '--dy': `${piece.dy}px`, '--spin': `${piece.spin}deg`, color: piece.colour }}
            >
              {piece.shape}
            </span>
          ))}
        </span>
      ))}
    </div>
  );
}
