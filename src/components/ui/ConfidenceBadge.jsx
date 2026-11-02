/* Where a bill line comes from, in plain words (src/lib/plainWords.js); hover for the
   full meaning. A line can carry its own words when the flag alone would mislead, such as a
   measured length with an assumed ceiling. Reuses the .afp-conf-* colour classes in tokens.css. */
import { SOURCE } from '../../lib/plainWords';

export default function ConfidenceBadge({ source, label }) {
  const s = SOURCE[source];
  return (
    <span className={`afp-conf-${source}`} title={s?.meaning} style={{ fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', cursor: s ? 'help' : undefined }}>
      {label || s?.label || source}
    </span>
  );
}
