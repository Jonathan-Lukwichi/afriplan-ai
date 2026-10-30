# Companion and derivation rules — the canonical table

One table, used by two skills: `deriving-companion-items` emits these lines, `checking-boq-completeness`
checks them. Change a rule here only through `improving-boq-skills` (evidence in `FEEDBACK.md`).

`A ⇒ B` = if A is in the bill, B must be too, with this quantity. **Conf** = H / M / L as defined in
`improving-boq-skills`. **Gate** = the scope modifier (skill `reading-scope-modifiers`) that switches the
rule off or changes it.

Sources — public SA tender bills in `doe/knowledge/example_boqs/` (local copies, see `SOURCES.md`):
UNP = Unpriced_-ELECTRICAL-Bill-of-Quantities (15 block bills) · PTC = Part C - Electrical BoQ ·
VUT = T012025 · BPR = 1-BOQ-B-Electrical · DRB = DR-BLOK · EX3 = Example-BOQ-3 · NEC = NEC Annexure ·
RPS = REVISED PRICING SCHEDULE. `pN` = page N of the `.txt` copy. "Script-verified" = checked by
arithmetic across the bill, not by eye.

## Layer model (why there are two hidden layers)
```
COUNTS ─► ROUTE: conduit[Ø, material] = R (horizontal route) + D (drops)      fallback: points × m/point (ASSUMED)
ROUTE  ─► conductors, circuit earth, draw wire, round boxes ─► dome lids, chasing
COUNTS ─► wall boxes, engraving, 5 A plugs, isolators, blank plates
SLD    ─► terminations, feeder earth, trench ─► backfill, tape, sleeves ─► seals
```
Most wiring material is a function of the **route**, not of the point count. Fitting ratios straight
from counts (`api/evaluation/ratios.py`) skips the route layer.

## CO-F — feeders and underground (per feeder finding)
| ID | Primary ⇒ companion | Quantity | Gate (off / changes when) | Conf | Evidence |
|---|---|---|---|---|---|
| CO-F1 | SWA cable size S, length L ⇒ Supply + Install rows | both = L | rates combined (one all-in line) | H | BPR, VUT, UNP |
| CO-F2 | SWA cable **without ECC** ⇒ earth (BCEW) on the same route | m = L | `ecc_cable` → no earth line | H | UNP p4–7 (4/6 sizes exact, script-verified), DRB p2, EX3 p7 |
| CO-F3 | Earth size for cable S | ≤16 mm²: same size · 25–35: 16 · ≥50: about half (70→35, 120→70, 240→120) | drawn/scheduled size wins | M — verify against SANS 10142-1 before changing `earth_size_for` | DRB p2, UNP p4–8 |
| CO-F4 | SWA run ⇒ cable terminations size S | **2 per run**, both billed in the bill that carries the cable (also the supply-end one) | — | H | DRB p2–3, PTC p4, VUT p5, EX3 p7–8 |
| CO-F5 | Earth run ⇒ earth terminations | 1–2 per run (bills differ) | CO-F2 off | M | DRB p3 (1/run), UNP (2/run) |
| CO-F6 | Each cable size used ⇒ straight joint | qty 0 or 1, PROVISIONAL rate line | client bill has no joints | L | UNP p4–8, EX3 |
| CO-F7 | Buried route R (shared trench once) ⇒ trench | m, or m³ = R × depth × width when the text gives dims | `excluded:excavation` | H | EX3 p4, p6; PTC p5 |
| CO-F8 | Trench excavation ⇒ backfill & compaction | = Σ excavation (all soil classes) | CO-F7 off | M (one bill exact) | PTC p5 (script-verified) |
| CO-F9 | Trench R ⇒ warning tape | m = R | only an explicit note removes it — "excavations by builder" alone keeps tape ASSUMED + GapItem (laying tape is often still the electrician's) | M | EX3 p6, PTC p6, BPR p10 |
| CO-F10 | Excavation by soil class | rock ≈ 2 %, intermediate ≈ 3 % of volume, PROVISIONAL extra-over | geotech report states classes | L | PTC p5 |
| CO-F11 | Road/paving crossing ⇒ sleeve m + **2 end seals per sleeve** + draw cord in spare sleeves | per crossing | `excluded:sleeves` | M | EX3 p4, p6; UNP p8–9 |
| CO-F12 | Kiosk / minisub ⇒ plinth + earth electrode set | 1 each per unit | included in the kiosk line | H | EX3 p5, UNP p1 |
| CO-F13 | Earth pit ⇒ 2 × electrodes + 1 joining sleeve | per pit | — | L | UNP p94 |

## CO-C — final circuits and containment (per building)
| ID | Primary ⇒ companion | Quantity | Gate | Conf | Evidence |
|---|---|---|---|---|---|
| CO-C1 | Conduit | R + D per circuit (lighting/power may differ in Ø) | `wiring_method` = surfix → no conduit | H | BOQ_KNOWLEDGE §4–5 |
| CO-C2 | Conduit when no route measured | points × 7–10 m, ASSUMED + GapItem | — | L | BOQ_KNOWLEDGE §4 |
| CO-C3 | Conduit ⇒ GP conductors (all sizes) | 2.0–2.2 × conduit m | surfix | H | UNP all blocks (2.0), PTC p9 (2.2 = 2 × 10 %) |
| CO-C4 | GP conductors ⇒ circuit earth wire | **Σ conductors ÷ 2, per size** (1.5 mm² circuits → 1.5 mm² earth, 2.5 → 2.5) | surfix (earth inside) | H | UNP, PTC p9, VUT p7 — three consultants, exact |
| CO-C5 | Conductor sizes | lighting 1.5 · power 2.5 · dedicated 4 mm² (or per SLD) | SLD states size | H | PTC p9 |
| CO-C6 | Colours | red + black on the route, + white on lighting switch legs | spec without colours → one line per size | M | BOQ_KNOWLEDGE §3, RPS p3 |
| CO-C7 | Conduit (Ø ≤ 25, all materials) ⇒ draw wire | **m = total conduit m** | only when spec asks, or empty conduits | H | UNP ~13/15 blocks exact (script-verified), PTC p51 |
| CO-C8 | Conduit ⇒ round / looping boxes | conduit m ÷ 3 to ÷ 7; never fewer than ceiling points | counted boxes win | M | UNP (÷3, script-verified), PTC p9 (÷7) |
| CO-C9 | Round boxes ⇒ dome lids (same material) | **= round boxes** | — | H | UNP all blocks (script-verified) |
| CO-C10 | Light switches ⇒ 100×50 wall box | = switches | `included:boxes` | H | PTC p7, p9; UNP |
| CO-C11 | Switched sockets + boxed isolators (+ flush data) ⇒ 100×100 wall box | = sum | `included:boxes` | H | PTC p7, p9; UNP |
| CO-C12 | Boxes − fitted accessories ⇒ blank cover plates | difference | — | L | NEC p41 |
| CO-C13 | Switched accessories ⇒ engraving of circuit numbers | = switches + sockets + isolators (not unswitched luminaire sockets) | spec has no engraving clause | M | UNP p14 |
| CO-C14 | Plug-in luminaire (grid/recessed ceiling) ⇒ 5 A unswitched socket + 3 m flex | = those luminaires | `plug_and_cabtyre` note, or ceiling gate | M | NEC p35, BPR p6 |
| CO-C15 | Drops in masonry ⇒ chasing | per drop, banded by height | wall gate: drywall → none | M | BOQ_KNOWLEDGE §3 |
| CO-C16 | Fixed appliance ⇒ isolator | 20 A DP geyser/dryer/fan · 30 A DP AC/signage · IP66 outdoors | — | H | BPR p2, VUT p8 |
| CO-C17 | Trunking / tray m ⇒ cover m + bends/tees/end caps | cover = run; fittings counted | cover included | H | BPR p7, p9 |
| CO-C18 | Wiring duct ⇒ splice / hanger / retainer | 1 per 3 m / 1.5 m / 1 m; 1 outlet per DB | — | L | PTC p10 |
| CO-C19 | Site pole light ⇒ pole + pole excavation + install pole + install fitting | 1 each; fittings = poles × heads | — | H | UNP p15, EX3 p9 |
| CO-C20 | Roof ⇒ lightning down conductors | max(2, roof perimeter ÷ 30 m); per conductor: test-joint box, terminations, 2 electrodes + sleeve; PVC conduit = conductor length | not designed → PROVISIONAL per m² roof | M | PTC p11, p50; UNP p90–91 |

## CO-B — per bill (each building bill and the LV network bill)
CO-B1–B3 are **priced Sums** the tenderer prices (AfriPlan tag ASSUMED), not contractual provisional
sums — they get no P&A line. CO-B4 applies only to sums the bill itself calls provisional or PC.

| ID | Companion | Unit | Tag | Conf | Evidence |
|---|---|---|---|---|---|
| CO-B1 | Earthing & bonding to SANS 10142-1 | Sum | ASSUMED | H (6/7 bills) | UNP p9–10, DRB p4, EX3 p8 |
| CO-B2 | Test & commission incl. Certificate of Compliance | Sum | ASSUMED | H (5/7) | UNP p16, EX3 p9, VUT p3 |
| CO-B3 | As-built drawings (often × 3) / O&M manuals / training | Set / Sum | ASSUMED | M (4/7) | UNP, EX3, PTC |
| CO-B4 | Every contractual provisional or PC sum ⇒ its own profit & attendance % line | % | PROVISIONAL | H | PTC p4, p11–12; BPR p13 |
| CO-B5 | Board ⇒ labels, CoC/test, spare ways ≥ 15 % (or spec %, up to 30 %) | per board | INFERRED | M | VUT p4, `api/core/standards.py` |

## Never in the quantity
Waste and off-cuts stay **in the rate** (`core/rate_model.py` waste), never in the measured quantity:
SA preambles say cables are "measured between terminations" (UNP p1, PTC Part 4 §15).
