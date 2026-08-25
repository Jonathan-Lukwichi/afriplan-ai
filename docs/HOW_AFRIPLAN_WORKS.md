# How AfriPlan works — a plain-English guide

This guide is for anyone using AfriPlan for the first time who is **not**
a software person: a contractor, a project manager, an estimator, or a
client trying to understand a quotation they were sent. No jargon is
assumed. Where a technical term is unavoidable, it's explained the first
time it's used, and again in the glossary at the end.

---

## 1. What AfriPlan does, in one paragraph

You give AfriPlan a set of electrical drawings for a building. AfriPlan
reads them, counts everything on them (distribution boards, sockets,
lights, cable runs, and so on), checks the result against South Africa's
electrical wiring standard (SANS 10142-1:2017), and turns all of that into
a priced Bill of Quantities ("BoQ" — see glossary) and a quotation you can
send to a client. What used to take a person hours of manual counting
happens in a couple of minutes.

---

## 2. The journey, step by step

AfriPlan is organised as a set of pages down the left-hand sidebar. You
move through them roughly top to bottom for every new project:

**Welcome → Upload → Take-off → (Compare) → BoQ & quotation → Pricing**

| Step | What you do | What AfriPlan does | What you see when it's done |
|---|---|---|---|
| **Welcome** | Click "Upload a drawing" | Nothing yet — this is just the start screen | The Upload page |
| **Upload** | Choose which kind of drawing file(s) you have, then pick them from your computer | Sends the file(s) to the engine you chose (see section 3) | You're taken to the Take-off page while it works |
| **Take-off** | Wait a few seconds (DXF) to a minute or two (PDF) | Reads every symbol on the drawing and turns it into a countable list of items | A status card, three summary numbers, and a "Legend" table of everything found |
| **Compare** *(only if you ran "Both")* | Nothing — just review | Runs the DXF and PDF engines on the same job and lines their results up side by side | A table showing where the two engines agree and where they don't |
| **BoQ & quotation** | Set your markup/contingency/tax, review the bill | Turns the counted items into priced line items, checked against SANS 10142-1 | A priced bill you can download as Excel or PDF, or email directly |
| **Pricing** *(optional)* | Choose which items to price-check | Requests quotes from a panel of suppliers for those items | A comparison table you can use to swap in a cheaper price before you finalise the BoQ |

Nothing is billed or finalised automatically — every step ends with
something for you to read and decide on before moving to the next one.

---

## 3. Two engines, explained simply

AfriPlan has two independent ways of reading a drawing. They never share
information with each other — each one works the job out from scratch, on
its own. This is deliberate: it means you can run both and use one as a
sanity check on the other.

- **DXF engine** — for drawings exported from CAD software as a `.dxf` or
  `.dwg` file (the file formats AutoCAD and similar programs save in). This
  engine reads the exact geometry of the drawing — it doesn't "look" at a
  picture, it reads the underlying data, so it's fast, free to run, and
  extremely precise. If you upload a `.dwg` file, AfriPlan quietly converts
  it to `.dxf` first — you don't need to do anything differently.
- **PDF engine** — for drawings you only have as a scanned or exported PDF
  (no underlying CAD data). This engine uses an AI vision model to
  literally look at each page, the same way a person would, and work out
  what it's seeing. It's slower (each page takes up to about a minute) and,
  unlike the DXF engine, it has a small real running cost per page — but it
  means you can still get a bill from a PDF-only drawing set with no CAD
  file behind it.
- **Both, compare** — runs the same job through both engines and shows you
  a side-by-side comparison. Useful when you want extra confidence in the
  result, or when you're not sure if your PDF is a faithful copy of the
  original CAD file.

---

## 4. How to read a Take-off result

The Take-off page is the first result you'll see after uploading. Here's
what each part means:

- **Engine badge** (top left, e.g. "DXF ENGINE") — tells you which engine
  produced this result.
- **Status** — "Passed" means the drawing was read successfully and a bill
  can be generated. "Failed" means something went wrong (see the FAQ).
- **The three summary numbers**:
  - *Line items* — how many distinct billable items were found.
  - *Gaps flagged* — how many of those items needed an assumption because
    something wasn't fully clear on the drawing (see section 5 — this
    isn't automatically a problem, but it is always worth a glance).
  - *Total incl. VAT* — a preview of the final price; the full breakdown
    lives on the BoQ page.
- **Legend table** — every distinct symbol AfriPlan recognised on the
  drawing, one row per symbol: what it looked like (**Symbol**), what it is
  in plain terms (**Description**), what AfriPlan is calling it internally
  for pricing purposes (**Canonical Item**), which part of the bill it
  belongs to (**Section**), and how many were counted (**Qty**).

---

## 5. The confidence badges — the single most important thing in this guide

Every line item AfriPlan produces — in the Legend table and in the BoQ line
items table — is tagged with a small coloured label. This label always
means the same thing everywhere in the app, and it's the fastest way to
know how much to trust a number before you send it to a client.

| Badge | Colour | What it means |
|---|---|---|
| **Extracted** | Green | Read directly off the drawing. The highest level of trust — this is a real, measured count. |
| **Inferred** | Teal | Not read directly, but worked out automatically and reliably from other extracted data (e.g. cable length calculated from a known route). |
| **Assumed** | Amber | A quantity that AfriPlan had to estimate, using a stated, documented assumption — the assumption is written out for you in the Gap report (section 6) so you can check it. |
| **Provisional** | Grey | A placeholder allowance, not something actually measured off the drawing. Needs a real number before this goes to tender. |
| **Estimated** | Red | A rough guess with no supporting data behind it. Always worth reviewing before you rely on it. |
| **Manual** | Blue | Someone (you, or a colleague) typed this value in by hand. |

**Rule of thumb:** green and teal — trust it. Amber — read the assumption
and confirm it's reasonable for your project. Grey and red — don't send
these to a client without checking them yourself first. Blue — that's your
own input, so it's only as accurate as what was typed in.

---

## 6. How to read the BoQ & quotation page

This is where a Take-off result becomes an actual, priced document you can
send out.

- **Pricing inputs** (top of the page):
  - *Markup %* — your profit margin, added on top of material/labour cost.
  - *Contingency %* — a buffer added for the unexpected (price changes,
    small scope surprises).
  - *VAT %* — South Africa's value-added tax rate, applied to the final
    total.
  - *Quote reference* / *Validity (days)* — just labelling for the document
    you'll send; leave "Quote reference" as "auto" if you don't need a
    specific one.
  Changing any of these instantly recalculates every number on the page —
  nothing here is locked in until you actually download or send the
  document.
- **The four money tiles**:
  - *Subtotal* — the raw cost of every line item added together, before
    markup/contingency/VAT.
  - *Total ex VAT* — subtotal plus your markup and contingency, still
    without tax.
  - *VAT* — the tax amount itself, calculated from "Total ex VAT".
  - *Total incl. VAT* — the final number your client actually pays.
- **Section subtotals** — a bar chart showing which parts of the job
  (distribution boards, cabling, outlets, etc.) make up the biggest share
  of the cost — useful for a quick gut-check on where the money is going.
- **Line items table** — the full itemised bill: section, description,
  unit, quantity, rate, line total, and a **Source** column, which is
  exactly the same confidence badge described in section 5.
- **Gap report** — the honest part of the app. Every item that needed an
  assumption is listed here in plain language: what was assumed, why, and
  what you should do about it (verify it, measure it, or accept it as-is).
  This exists so nothing is silently guessed without you knowing.
- **Downloads** — Excel (`.xlsx`) for further editing, or a formatted PDF
  quotation ready to send.
- **Email this BoQ** — sends the quotation as an email attachment directly
  from the app, without you needing to download and re-attach it yourself.

---

## 7. Live Pricing (optional)

If you want to price-check the BoQ against real supplier options before
you finalise it, the Pricing page lets you do that:

1. **Choose items** — tick which line items you want quotes for.
2. **Compare & choose** — AfriPlan requests pricing from a panel of
   suppliers for each item and shows you unit price, stock availability,
   and delivery lead time side by side, with a star (★) marking the
   recommended option. For each item you can pick "Keep BoQ estimate" or
   swap in one of the supplier quotes.
3. **Apply to BoQ** — pushes your chosen prices back into the bill, and
   shows you how the subtotal moved as a result.

There's also an **RFQ email** tool further down the page for suppliers who
only give pricing on request rather than online: it drafts a professional
request-for-quote email for you, and once you get a reply back, you can
paste it in and AfriPlan will read the numbers out of it into the same
comparison format.

**Worth knowing:** the supplier panel on this page is a simulated set of
suppliers for demonstration purposes, not live connections to real
merchants — treat the numbers as realistic market pricing to sanity-check
your own rates against, not as an actual live quote from a real supplier.

---

## 8. FAQ

**Why does my Take-off say "Failed"?**
The engine couldn't successfully read the drawing — usually because the
file wasn't the format expected (e.g. a DXF pipeline given a corrupted
file), or, for the PDF engine specifically, because the AI service it
depends on wasn't available at that moment. It's not silently producing a
wrong answer — it's telling you it couldn't produce a trustworthy one at
all.

**What should I do with an amber or red item?**
Read its entry in the Gap report — it tells you exactly what was assumed
and what to check. A quick site measurement or a look at the original
drawing usually resolves it.

**Does running the PDF engine cost money?**
Yes — a small real cost per page, because it uses a paid AI service to
read each drawing sheet. The DXF engine is free to run, since it reads the
CAD file's own data directly rather than using AI.

**What's the actual difference between the two engines again?**
DXF reads the precise underlying CAD data (fast, free, needs a real CAD
export). PDF reads the visual page like a person would (slower, small
cost, works from scans or exported PDFs with no CAD file behind them).

**Can I trust the SANS check?**
The bill is checked against SANS 10142-1:2017 automatically as part of
generating the BoQ — but that check is a tool to help you, not a
substitute for your own professional sign-off on the final document.

---

## 9. Glossary

- **BoQ (Bill of Quantities)** — an itemised list of everything needed for
  a job, with quantities and prices, that adds up to a total cost.
- **Take-off** — the industry term for counting up everything shown on a
  drawing (how many sockets, how much cable, etc.) before pricing it.
- **SLD (Single Line Diagram)** — a simplified drawing showing how
  electrical power flows and is distributed through a building.
- **SANS 10142-1** — the South African national standard for the wiring of
  premises; the rulebook AfriPlan checks a bill against.
- **VAT (Value-Added Tax)** — South Africa's sales tax, added to the final
  price of goods and services.
- **Contingency** — a percentage added to a quote as a buffer for
  unexpected costs.
- **Markup** — the percentage added on top of raw cost as profit margin.
- **DB (Distribution Board)** — the board (sometimes called a "breaker
  board") that splits incoming electrical power into individual circuits
  around a building.
- **Confidence badge** — the coloured label (Extracted/Inferred/Assumed/
  Provisional/Estimated/Manual) that tells you how trustworthy a given
  number is; see section 5.
- **Engine / pipeline** — AfriPlan's internal name for one of the two
  independent ways of reading a drawing (DXF or PDF); see section 3.
- **RFQ (Request For Quote)** — a formal email asking a supplier for
  pricing on specific items.
- **DWG** — another CAD drawing file format (used by AutoCAD); AfriPlan
  converts it to DXF automatically before reading it.
