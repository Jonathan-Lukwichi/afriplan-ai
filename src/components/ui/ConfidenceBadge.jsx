/* The 6-way ItemConfidence mapping (agent/shared/boq.py) — documented in
   the original app but never actually rendered in its Streamlit UI. Reuses
   the .afp-conf-* color classes already defined in tokens.css. */
const LABEL = {
  extracted: 'Extracted',
  inferred: 'Inferred',
  assumed: 'Assumed',
  provisional: 'Provisional',
  estimated: 'Estimated',
  manual: 'Manual',
};

export default function ConfidenceBadge({ source }) {
  return (
    <span className={`afp-conf-${source}`} style={{ fontSize: 12, fontWeight: 600 }}>
      {LABEL[source] || source}
    </span>
  );
}
