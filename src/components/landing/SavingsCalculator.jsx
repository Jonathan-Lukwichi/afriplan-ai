import { useState } from 'react';

/* "What take-off costs you now" — every number comes from the visitor's own
   sliders, including how much of the take-off they expect the first draft
   to save. Nothing here is a measured AfriPlan claim. */

const FIELDS = [
  { key: 'tenders', label: 'Tenders you price a month', min: 1, max: 40, step: 1, fmt: (v) => `${v}` },
  { key: 'hours', label: 'Hours of take-off per tender', min: 2, max: 40, step: 1, fmt: (v) => `${v} h` },
  { key: 'cost', label: 'Estimator cost per hour', min: 150, max: 1500, step: 50, fmt: (v) => `R ${v.toLocaleString('en-ZA')}` },
  { key: 'share', label: 'Share of take-off time the first draft saves', min: 20, max: 80, step: 5, fmt: (v) => `${v}%` },
];

export default function SavingsCalculator() {
  const [v, setV] = useState({ tenders: 6, hours: 16, cost: 450, share: 50 });
  const hoursBack = v.tenders * v.hours * (v.share / 100);
  const randBack = hoursBack * v.cost;
  const hoursPerTenderAfter = v.hours * (1 - v.share / 100);
  const extraTenders = Math.floor(hoursBack / hoursPerTenderAfter);

  return (
    <div className="lp-calc">
      <div className="lp-calc-inputs">
        {FIELDS.map((f) => (
          <div key={f.key} className="lp-calc-field">
            <label htmlFor={`calc-${f.key}`}>
              <span>{f.label}</span>
              <output htmlFor={`calc-${f.key}`} className="num">{f.fmt(v[f.key])}</output>
            </label>
            <input
              id={`calc-${f.key}`}
              type="range"
              min={f.min}
              max={f.max}
              step={f.step}
              value={v[f.key]}
              onChange={(e) => setV({ ...v, [f.key]: Number(e.target.value) })}
              style={{ '--fill': `${((v[f.key] - f.min) / (f.max - f.min)) * 100}%` }}
            />
          </div>
        ))}
      </div>

      <div className="lp-calc-out" aria-live="polite">
        <div className="lp-calc-big">
          <span className="lp-calc-big-num num">R {Math.round(randBack).toLocaleString('en-ZA')}</span>
          <span>of estimator time back every month, about R {Math.round(randBack * 12).toLocaleString('en-ZA')} a year</span>
        </div>
        <dl className="lp-calc-small">
          <div>
            <dt>Hours back a month</dt>
            <dd className="num">{Math.round(hoursBack)}</dd>
          </div>
          <div>
            <dt>Extra tenders in those hours</dt>
            <dd className="num">+{extraTenders}</dd>
          </div>
          <div>
            <dt>Take-off per tender</dt>
            <dd className="num">{v.hours} h to {Math.round(hoursPerTenderAfter * 10) / 10} h</dd>
          </div>
        </dl>
        <p className="lp-calc-note">
          Your figures and your assumption. Set the last slider to what you see on your own drawings
          after the first few runs.
        </p>
      </div>
    </div>
  );
}
