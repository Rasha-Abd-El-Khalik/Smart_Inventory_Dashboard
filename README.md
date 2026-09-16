# Smart Inventory Dashboard API

A config-driven dashboard resolver: one **widget catalog** (`app/catalog.py`)
declares every KPI/chart/table across 6 dashboards, and a generic
**resolver** (`app/resolver.py`) turns that catalog + a business's
column-mapping into live MySQL queries and a JSON response.

## Endpoint

```
GET /businesses/{business_id}/dashboard
```

| Param | Required | Notes |
|---|---|---|
| `business_id` | yes (path) | whose data to compute |
| `dashboard` | no | **multi-select**. Repeat the param (`?dashboard=sales&dashboard=operations`) or comma-separate (`?dashboard=sales,operations`). Omit → all 6 dashboards. Values: `sales`, `inventory`, `suppliers`, `purchasing`, `products`, `operations` |
| `start_date`, `end_date` | no | ISO dates, must be given together. Only affects time-series (`line`) widgets |
| `preset` | no | `last_7_days` \| `last_30_days` \| `last_90_days` \| `last_365_days`, alternative to start/end date |
| `granularity` | no | `day` (default) \| `week` \| `month` — bucketing for `line` widgets |

### Response shape

```json
{
  "business_id": 123,
  "generated_at": "2026-09-07T10:00:00Z",
  "dashboards": {
    "sales": {
      "widgets": [
        { "id": "total_revenue", "type": "kpi", "title": "Total Revenue", "value": 48210.5 },
        {
          "id": "revenue_by_payment_type", "type": "bar",
          "title": "Revenue by Payment Type",
          "x_axis": { "label": "Payment Method", "data": ["CARD", "CASH"] },
          "y_axis": { "label": "Amount Paid", "data": [107.0, 20.0] }
        }
      ]
    }
  }
}
```

## The three confirmed design decisions this implements

1. **Unavailable widgets are omitted, not flagged.** If a business's column
   mapping doesn't cover everything a widget needs, that widget simply does
   not appear in the response — no `available: false` placeholder object.
   (See `resolver._resolve_widget`: returns `None` → filtered out.)

2. **`dashboard` is multi-select.** Accepts repeated query params AND a
   comma-separated single value; de-duplicates while preserving order.
   Omitting it returns every dashboard. (See `main._parse_dashboard_param`.)

3. **Labels use the business's own original column names, not our
   canonical schema names** — for any widget/axis backed by exactly ONE
   canonical column. E.g. if `order_item.extended_price` was mapped from
   the client's own `line_total` column, any axis/KPI driven purely by that
   column is labeled **"Line Total"**, not "Extended Price".
   For **computed/derived** metrics that combine more than one column
   (margin, average order value, average tenure, etc.) there is no single
   source column to name it after, so those fall back to a fixed
   descriptive English name (e.g. "Gross Margin", "Average Tenure (Days)").
   A chart's overall *title* always uses the fallback name too, since every
   chart inherently combines an x dimension and a y measure.

## How the column mapping is expected to work

The mapping is now supplied as a **JSON file per business**, one row per
canonical column, at `app/data/business_mappings/{business_id}.json`:

```json
[
  {"our_schema": "order_item.extended_price", "user_column": "order_items.line_total"},
  {"our_schema": "product.cost", "user_column": null}
]
```

| Field | Required | Meaning |
|---|---|---|
| `our_schema` | yes | One of the fixed canonical refs in `CANONICAL_SCHEMA` (`app/mapping.py`) — **our** side of the schema, the same for every business. |
| `user_column` | yes | `"table.column"` as it actually exists in **this business's** database. If the business genuinely doesn't have this column, this must be explicit — `null` (or the strings `"NOT_MATCHED"` / `"N/A"`, case-insensitive). Never just leave the row out silently. |
| `user_label` | no | The column name as the business originally wrote it, used for chart/KPI labels. If omitted, it's auto-derived from the column part of `user_column` (e.g. `line_total` → `Line Total`). |

**Any canonical column left unmatched (`null` / `NOT_MATCHED` / missing
from the file) simply stays unmapped** — any widget that requires it is
silently omitted from the dashboard response, same as before. No other
code needed to change for this.

A ready-to-fill template with every canonical column already listed
(`user_column: null`) lives at
`app/data/business_mappings/_template.json` — copy it, fill in
`user_column` for every row the business has, save it as
`{business_id}.json`, done. `app/data/business_mappings/123.json` is a
filled example (mirrors the old demo data) so the service runs standalone
out of the box.

**To go to production** with a different storage backend (DB table,
cache, API call, etc. instead of a JSON file on disk): only
`get_business_mapping()` in `app/mapping.py` needs to change — keep
returning `build_mapping_from_entries(business_id, entries)` and nothing
else in the service needs to change. If no mapping file exists for a
`business_id`, the service returns an empty mapping (all widgets omitted)
instead of erroring.

## How the resolver builds SQL

Every widget's `sql` field is a template using placeholders:

- `{entity.column}` → resolved to `` `real_table`.`real_column` `` for this business
- `{entity.__table__}` → resolved to `` `real_table` ``
- `{bucket_expr}` (line charts only) → a granularity-aware time-bucket expression
- `{date_filter}` (line charts only) → an optional `AND col BETWEEN ... AND ...` clause

Availability is checked with `ColumnMapping.has_all(widget.required_columns)`
*before* any SQL is built — so a widget's placeholders are only ever
substituted when every ref it needs is actually mapped.

> Placeholder substitution is done with plain regex (`resolver._render_sql`),
> deliberately **not** `str.format()` — Python's format mini-language treats
> a dot in `{a.b}` as attribute access (`getattr`), not a dict-key lookup,
> which would silently break every `{entity.column}`-style placeholder.

## Adding a new widget

Add one `WidgetDef` entry to `app/catalog.py`:

```python
WidgetDef(
    id="my_new_widget",
    dashboard="sales",
    chart_type="kpi",              # kpi | bar | pie | line | table
    title_fallback="My New Widget",# used when the metric is computed
    required_columns=["order.order_id"],
    sql="SELECT COUNT({order.order_id}) AS value FROM {order.__table__}",
    value_ref="order.order_id",    # None if computed from >1 column
),
```

Nothing else needs to change — the resolver and endpoint pick it up
automatically.

## Running locally

```bash
pip install -r requirements.txt

# Point at your MySQL instance:
export DB_HOST=localhost DB_PORT=3306 DB_USER=root DB_PASSWORD=secret DB_NAME=smart_inventory

uvicorn app.main:app --reload
```

Then:

```
GET http://localhost:8000/businesses/123/dashboard
GET http://localhost:8000/businesses/123/dashboard?dashboard=sales,operations&preset=last_90_days&granularity=week
```

## Known simplifications (documented, not hidden)

- `INVENTORYITEM.status` value for "in stock" is hardcoded as the literal
  `'available'` (`items_in_stock`, `low_stock_products`) — move to
  `app/config.py` per-business if your status values vary.
- `LOW_STOCK_THRESHOLD` (`app/config.py`) is a single global constant (10
  units) — make it per-business/per-product if needed.
- Joins are written explicitly per widget rather than auto-derived from the
  ERD's FK relationships, so each widget's SQL is easy to read/audit —
  there is no generic join-planner.
- `average_delivery_delay` and `average_tenure` use MySQL's `DATEDIFF`/
  `CURDATE()` — fine on real MySQL, but won't run as-is against SQLite
  (only relevant if you swap the DB layer for local testing, as this
  project's own smoke test does).
