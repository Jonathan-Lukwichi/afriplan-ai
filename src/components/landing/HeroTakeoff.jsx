import { useEffect, useState } from 'react';

/* Landing hero: a drawing sheet beside the bill it produced. Pointing at a
   bill line highlights the symbols it was taken from, the way an estimator
   marks up a printed sheet; the ASSUMED line highlights nothing and says so.
   Drawing, quantities and rates are illustrative — no client data. */

const ITEMS = [
  { key: 'panel',  ref: 'L1',   desc: 'LED panel 600 × 600, recessed',   unit: 'No', qty: 17,  rate: 1150, evidence: 'counted' },
  { key: 'socket', ref: 'P1',   desc: 'Double socket outlet, 16 A',      unit: 'No', qty: 10,  rate: 385,  evidence: 'counted' },
  { key: 'switch', ref: 'S1',   desc: 'One-lever light switch',          unit: 'No', qty: 5,   rate: 210,  evidence: 'counted' },
  { key: 'wire',   ref: 'W1',   desc: '2.5 mm² GP wire in 20 mm conduit', unit: 'm',  qty: 186, rate: 42,   evidence: 'measured' },
  { key: 'db',     ref: 'DB-1', desc: 'Distribution board, 24-way',      unit: 'No', qty: 1,   rate: 8900, evidence: 'written' },
  { key: 'surge',  ref: 'SP1',  desc: 'Surge protection, Type 2',        unit: 'No', qty: 1,   rate: 2450, evidence: 'assumed' },
];

const EVIDENCE_NOTE = {
  counted: 'Counted on the drawing',
  measured: 'Measured on the drawing, to scale',
  written: 'Read from the DB schedule',
  assumed: 'Not on the drawing. Priced from an assumption and listed as a gap',
};

const PANELS = [
  [75, 75], [145, 75], [75, 140], [145, 140],
  [255, 65], [320, 65], [385, 65], [440, 65], [255, 140], [320, 140], [385, 140], [440, 140],
  [95, 255], [175, 255], [255, 255],
  [375, 255], [425, 255],
];
const SOCKETS = [[28, 60], [28, 170], [110, 28], [300, 28], [452, 100], [452, 170], [28, 240], [160, 312], [452, 240], [400, 312]];
const SWITCHES = [[190, 132], [138, 210], [415, 190], [340, 270], [282, 310]];
const WIRES = [
  'M56 286 H95 V255 H425',
  'M41 278 V140 H145 V75 H75 V140',
  'M56 292 H320 V140 H440 V65 H255 V140',
  'M320 65 V140 M385 65 V140',
];

const rand = (n) => `R ${Math.round(n).toLocaleString('en-ZA')}`;

function useCountUp(target) {
  const [n, setN] = useState(target);
  useEffect(() => {
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) return undefined;
    setN(0);
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setN(i);
      if (i >= target) clearInterval(id);
    }, 70);
    return () => clearInterval(id);
  }, [target]);
  return n;
}

export default function HeroTakeoff() {
  const [active, setActive] = useState('panel');
  const counted = useCountUp(PANELS.length);
  const item = ITEMS.find((i) => i.key === active);
  const qtyOf = (it) => (it.key === 'panel' ? counted : it.qty);
  const subtotal = ITEMS.reduce((s, i) => s + qtyOf(i) * i.rate, 0);
  const on = (key) => active === key;
  const dim = (key) => (active && !on(key) ? 0.35 : 1);

  return (
    <figure className="lp-takeoff" aria-label="Example: a lighting and power layout beside the Bill of Quantities taken from it">
      <div className="lp-takeoff-bar">
        <span className="lp-sheetref">WD-01</span>
        <span>Ground floor, lighting and power</span>
        <span className="lp-takeoff-bar-right">Bill 3, Electrical installation</span>
      </div>

      <div className="lp-takeoff-body">
        <div className="lp-sheet">
          <svg viewBox="0 0 480 340" role="img" aria-label={item ? `${item.desc}: ${EVIDENCE_NOTE[item.evidence]}` : 'Drawing'}>
            <defs>
              <pattern id="lp-grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M20 0H0V20" fill="none" stroke="#DCE3EE" strokeWidth="0.6" />
              </pattern>
              <pattern id="lp-hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <line x1="0" y1="0" x2="0" y2="4" stroke="#0F1B33" strokeWidth="1.4" />
              </pattern>
            </defs>
            <rect width="480" height="340" fill="url(#lp-grid)" />

            {/* walls, with door openings */}
            <g stroke="#0F1B33" strokeWidth="4" fill="none" strokeLinecap="square">
              <path d="M230 320 H20 V20 H460 V320 H270" />
              <path d="M200 20 V150 M200 180 V200" />
              <path d="M20 200 H100 M130 200 H380 M410 200 H460" />
              <path d="M330 200 V280 M330 310 V320" />
            </g>
            <g stroke="#0F1B33" strokeWidth="0.8" fill="none" opacity="0.5">
              <path d="M200 150 A30 30 0 0 1 230 180" />
              <path d="M100 200 A30 30 0 0 0 130 230" />
              <path d="M230 320 A40 40 0 0 1 270 280" />
            </g>
            <g fontFamily="IBM Plex Mono, monospace" fontSize="9" fill="#6B7590">
              <text x="30" y="190">OFFICE</text>
              <text x="210" y="190">OPEN PLAN</text>
              <text x="200" y="300">STORE</text>
              <text x="340" y="300">KITCHEN</text>
            </g>

            {/* wiring — dashed circuit runs */}
            {on('wire') && WIRES.map((d) => (
              <path key={`h${d}`} d={d} stroke="var(--highlighter)" strokeWidth="9" fill="none" strokeLinejoin="round" opacity="0.9" />
            ))}
            <g stroke="#2E5BE8" strokeWidth="1.3" strokeDasharray="5 4" fill="none" opacity={dim('wire')}>
              {WIRES.map((d) => <path key={d} d={d} />)}
            </g>

            {/* luminaires */}
            {PANELS.map(([x, y], i) => (
              <g key={`p${i}`} opacity={dim('panel')}>
                {on('panel') && i < counted && <circle cx={x} cy={y} r="14" fill="var(--highlighter)" />}
                <rect x={x - 8} y={y - 8} width="16" height="16" fill="#fff" stroke="#0F1B33" strokeWidth="1.3" />
                <path d={`M${x - 8} ${y - 8} L${x + 8} ${y + 8} M${x + 8} ${y - 8} L${x - 8} ${y + 8}`} stroke="#0F1B33" strokeWidth="0.9" />
              </g>
            ))}

            {/* socket outlets */}
            {SOCKETS.map(([x, y], i) => (
              <g key={`s${i}`} opacity={dim('socket')}>
                {on('socket') && <circle cx={x} cy={y} r="12" fill="var(--highlighter)" />}
                <circle cx={x} cy={y} r="6" fill="#fff" stroke="#0F1B33" strokeWidth="1.3" />
                <path d={`M${x - 2.2} ${y - 3} V${y + 3} M${x + 2.2} ${y - 3} V${y + 3}`} stroke="#0F1B33" strokeWidth="1.1" />
              </g>
            ))}

            {/* switches */}
            {SWITCHES.map(([x, y], i) => (
              <g key={`w${i}`} opacity={dim('switch')}>
                {on('switch') && <circle cx={x} cy={y} r="11" fill="var(--highlighter)" />}
                <circle cx={x} cy={y} r="3.6" fill="#0F1B33" />
                <path d={`M${x} ${y} L${x + 8} ${y - 8}`} stroke="#0F1B33" strokeWidth="1.3" />
              </g>
            ))}

            {/* distribution board */}
            <g opacity={dim('db')}>
              {on('db') && <rect x="18" y="270" width="46" height="30" rx="6" fill="var(--highlighter)" />}
              <rect x="26" y="278" width="30" height="14" fill="url(#lp-hatch)" stroke="#0F1B33" strokeWidth="1.3" />
              <text x="66" y="289" fontFamily="IBM Plex Mono, monospace" fontSize="8.5" fill="#0F1B33">DB-1</text>
            </g>
          </svg>

          <p className={`lp-sheet-note lp-ev-${item?.evidence}`} aria-live="polite">
            {item && (
              <>
                <strong>{item.ref}</strong> {EVIDENCE_NOTE[item.evidence]}
                {item.key === 'panel' && <span className="num">: {counted} of {PANELS.length}</span>}
              </>
            )}
          </p>
        </div>

        <div className="lp-bill">
          <div className="lp-bill-head" aria-hidden="true">
            <span>Item</span><span>Qty</span><span>Amount</span>
          </div>
          <ul className="lp-bill-rows">
            {ITEMS.map((it) => {
              const qty = qtyOf(it);
              return (
                <li key={it.key}>
                  <button
                    type="button"
                    className="lp-bill-row"
                    aria-pressed={on(it.key)}
                    onMouseEnter={() => setActive(it.key)}
                    onFocus={() => setActive(it.key)}
                    onClick={() => setActive(it.key)}
                  >
                    <span className="lp-bill-desc">
                      <span className="lp-bill-ref">{it.ref}</span>
                      <span>{it.desc}</span>
                      <span className={`lp-chip lp-chip-${it.evidence}`}>{it.evidence}</span>
                    </span>
                    <span className="lp-bill-qty num">{qty} {it.unit}</span>
                    <span className="lp-bill-amt num">{rand(qty * it.rate)}</span>
                  </button>
                </li>
              );
            })}
          </ul>
          <div className="lp-bill-foot">
            <span>Subtotal, excl. VAT</span>
            <span className="num">{rand(subtotal)}</span>
          </div>
          <p className="lp-bill-gap">1 line assumed. It is listed in the gap report for you to confirm.</p>
        </div>
      </div>
      <figcaption className="lp-takeoff-caption">Illustrative drawing and rates. Point at a line to see where its quantity came from.</figcaption>
    </figure>
  );
}
