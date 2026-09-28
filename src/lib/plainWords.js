/* Every word the app shows, in plain language — one place, so screens, the glossary
   and tooltips never disagree. Written for someone who has never read a drawing.
   The Excel/PDF exports use the same labels (api/exports/labels.py). */

// Where each bill line comes from (the "Source" of a line).
export const SOURCE = {
  extracted: {
    label: 'From the drawing',
    meaning: 'Counted or read directly off the drawings — e.g. sockets counted on the plan, a board’s breakers read from the wiring diagram.',
  },
  inferred: {
    label: 'Worked out',
    meaning: 'Calculated from what the drawings show — e.g. a cable length measured along its route on the site plan, plus a small allowance. Worth a quick check.',
  },
  assumed: {
    label: 'Guessed — check',
    meaning: 'Not shown on the drawings, so the app used a standard value (e.g. a 30 m cable). Each one is listed in the “Things to check” tab.',
  },
  provisional: {
    label: 'Allowance',
    meaning: 'Money set aside for work that is not designed yet.',
  },
  estimated: {
    label: 'Rough estimate — check',
    meaning: 'A rough figure with little evidence behind it. Check it before sending the quote.',
  },
  manual: {
    label: 'Price you chose',
    meaning: 'You changed this price — e.g. by picking a supplier’s price on the Pricing page.',
  },
};

// How urgent a warning is.
export const SEVERITY = {
  critical: { label: 'Must fix', meaning: 'Wrong as it stands — fix before using the bill.' },
  high: { label: 'Must check', meaning: 'Can change the price a lot. Check before sending the quote.' },
  medium: { label: 'Should check', meaning: 'Could change the price. Worth a look.' },
  low: { label: 'For information', meaning: 'Small or already handled — just so you know.' },
};

// Units on the bill.
export const UNITS = {
  Sum: { label: 'lump sum', meaning: 'One complete item priced as a whole (e.g. a full distribution board).' },
  No: { label: 'each', meaning: 'Number of items.' },
  Ea: { label: 'each', meaning: 'Number of items.' },
  m: { label: 'metres', meaning: 'Length in metres.' },
};

// Checks run by “Audit a BoQ”.
export const AUDIT_RULES = {
  ARITH: { label: 'Sum is wrong', meaning: 'Quantity × price does not equal the line total.' },
  UNTOTALLED: { label: 'Left out of the total', meaning: 'The line has a quantity and a price, but no total — so it is silently missing from the bill.' },
  NO_RATE: { label: 'No price', meaning: 'The line has a quantity but nobody priced it.' },
  DUPLICATE: { label: 'Same line twice', meaning: 'The exact same line appears more than once.' },
  REPEATED: { label: 'Priced twice, differently', meaning: 'The same item is priced more than once at different prices.' },
  ROLLUP: { label: 'Section total wrong', meaning: 'The lines of a section do not add up to the section total shown.' },
  CONTINGENCY: { label: 'Contingency wrong', meaning: 'The contingency is not the percentage the bill says it is.' },
  TOTAL: { label: 'Final total wrong', meaning: 'The building total does not equal its sections plus contingency.' },
  NOT_IN_SUMMARY: { label: 'Sheet missing from summary', meaning: 'A priced sheet is not included in the project summary, so its money is missing from the grand total.' },
  SUMMARY: { label: 'Summary disagrees', meaning: 'The summary shows a different amount from the sheet’s own total.' },
  ERROR_CELL: { label: 'Broken formula', meaning: 'A spreadsheet error such as #REF! or #VALUE!.' },
  COMPANION: { label: 'Missing partner item', meaning: 'A cable is billed without the things it always needs: its earth wire, its end connections or its installation.' },
};

// The words on the bill itself.
export const TERMS = [
  ['BoQ (Bill of Quantities)', 'The list of everything needed for the job, with how many of each and the price.'],
  ['Distribution board (DB)', 'The box full of switches (breakers) that sends power to a building or an area. “DB-AB1” is simply its name.'],
  ['Kiosk / Mini-sub', 'The mini-substation (mini-sub) is where the power company supplies the site; the kiosk is the main outdoor box fed from it.'],
  ['Wiring diagram (SLD)', '“Single-line diagram”: the drawing that shows the boards, their breakers and which cable feeds which board.'],
  ['Site plan', 'The drawing of the whole site. It shows where the cables run between the buildings — that is where cable lengths are measured.'],
  ['Feeder (sub-main cable)', 'The big cable that carries power from one board to another.'],
  ['SWA cable', 'Steel-wire-armoured cable: strong cable that can be buried in the ground.'],
  ['mm² (e.g. 95mm²)', 'How thick the copper inside a cable is. Bigger number = thicker cable = carries more power (and costs more).'],
  ['x4C', '4 copper wires (4 cores) inside the cable.'],
  ['BCEW earth', 'Bare copper earth wire: the safety wire laid next to a cable.'],
  ['Termination', 'Connecting the end of a cable to a board. Every cable has two ends, so two terminations.'],
  ['Trench / warning tape', 'The trench is the hole dug for the cable. Warning tape is laid above the cable so nobody digs into it later.'],
  ['Sleeve', 'A plastic pipe the cable passes through, e.g. under a road.'],
  ['3ph / 1ph', 'Three-phase (for bigger loads) or single-phase power.'],
  ['100A', 'The size of the board’s main switch, in amps.'],
  ['15kA', 'How strong a short-circuit the board can safely survive.'],
  ['31-way (7 spare)', 'The board has 31 slots for breakers; 7 are left empty for the future.'],
  ['Supply / Install', 'The material (supply) and the labour to fit it (install), priced on separate lines.'],
  ['Rate / Price each', 'The price for one unit — one metre of cable, one light, one board.'],
  ['Contingency', 'Extra money kept aside for surprises (5% unless you change it).'],
  ['Extra markup', 'Additional margin you add on top. The prices already include normal profit, so it starts at 0%.'],
  ['VAT', 'Value-added tax, 15%.'],
  ['Derived items', 'Items never drawn as symbols — wall boxes, wall cutting, conduit, wiring — added using ratios learned from a real priced project.'],
  ['Things to check (gap report)', 'Everything the app had to guess or could not confirm. Go through it before sending the quote.'],
];
