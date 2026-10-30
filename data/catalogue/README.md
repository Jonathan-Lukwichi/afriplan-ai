# Price catalogue

`price_catalogue.csv` / `.xlsx` — one row per product: supplier, part number, description, AfriPlan
family (mcb, mccb, socket, cable…), poles / amps / kA, list price excl. VAT, **price date**, and where
the price comes from (`price list`, `AfriPlan estimate`, `override: <who>`).

Built by `scripts/build_price_catalogue.py` from `doe/knowledge/price_lists/` and `api/core/constants.py`
(code: `api/sourcing/catalogue.py`). **Not committed**: supplier price lists are commercial documents
and the repo is public — every machine rebuilds its own.

## Changing a price
1. Open `price_overrides.csv` (created empty on the first build).
2. Add a row: `item_id` (from the catalogue), `list_price_zar_excl_vat`, `price_date` (YYYY-MM-DD),
   `updated_by`, `note` — and `discount_pct` for your trade discount.
   A row with a new `item_id` plus `supplier` and `description` adds your own item.
3. Rebuild. The overrides are applied on top; a rebuild never loses them.

Skill: `.claude/skills/consolidating-price-catalogue/`.
