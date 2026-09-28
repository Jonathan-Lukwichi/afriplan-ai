/* Where a bill line comes from, in plain words (src/lib/plainWords.js); hover for the
   full meaning. Reuses the .afp-conf-* colour classes defined in tokens.css. */
import { SOURCE } from '../../lib/plainWords';

export default function ConfidenceBadge({ source }) {
  const s = SOURCE[source];
  return (
    <span className={`afp-conf-${source}`} title={s?.meaning} style={{ fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', cursor: s ? 'help' : undefined }}>
      {s?.label || source}
    </span>
  );
}
