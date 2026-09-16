from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

CANONICAL_SCHEMA: List[str] = [

    "product.product_id",
    "product.product_name",
    "product.category_name",
    "product.cost",
    "product.retail_price",
    "product.lead_time",
    "product.discontinued",

    "category.category_name",

    "supplier.supplier_id",
    "supplier.account_balance",
    "supplier.country",

    "employee.employee_id",
    "employee.full_name",
    "employee.hire_date",
    "employee.termination_date",

    "order.order_id",
    "order.order_date",
    "order.order_status",
    "order.employee_id",

    "order_item.order_item_id",
    "order_item.order_id",
    "order_item.product_id",
    "order_item.supplier_id",
    "order_item.quantity",
    "order_item.extended_price",
    "order_item.discount",

    "payment.order_id",
    "payment.payment_type",
    "payment.payment_value",

    "inventory_item.inventory_item_id",
    "inventory_item.product_id",
    "inventory_item.supplier_id",
    "inventory_item.distribution_center_id",
    "inventory_item.status",

    "distribution_center.distribution_center_id",
    "distribution_center.distribution_center_name",
    "distribution_center.rental_cost",

    "stock_movement.product_id",
    "stock_movement.user_id",
    "stock_movement.type",
    "stock_movement.quantity",
    "stock_movement.created_at",

    "purchase_order.id",
    "purchase_order.supplier_id",
    "purchase_order.user_id",
    "purchase_order.status",
    "purchase_order.order_date",
    "purchase_order.expected_delivery_date",
    "purchase_order.received_at",
    "purchase_order.total_amount",

    "purchase_order_item.purchase_order_id",
    "purchase_order_item.product_id",
    "purchase_order_item.quantity_ordered",
    "purchase_order_item.quantity_received",
]

_NOT_MATCHED_MARKERS = {"", "null", "none", "not_matched", "n/a", "na"}

@dataclass(frozen=True)
class MappedColumn:

    table: str
    column: str
    user_label: str

class ColumnMapping:

    def __init__(self, business_id: int, mapping: Dict[str, MappedColumn], language: str = "en"):
        self.business_id = business_id
        self._mapping = mapping
        self.language = language if language in ("en", "ar") else "en"

    def has(self, canonical_ref: str) -> bool:
        return canonical_ref in self._mapping

    def has_all(self, canonical_refs: list[str]) -> bool:
        return all(self.has(ref) for ref in canonical_refs)

    def get(self, canonical_ref: str) -> Optional[MappedColumn]:
        return self._mapping.get(canonical_ref)

    def table_for_entity(self, entity: str) -> Optional[str]:
        prefix = f"{entity}."
        for ref, mapped in self._mapping.items():
            if ref.startswith(prefix):
                return mapped.table
        return None

def _humanize(column_name: str) -> str:
    return column_name.replace("_", " ").replace("-", " ").strip().title()

def _parse_user_column(user_column: str) -> tuple[str, str]:
    if "." not in user_column:
        raise ValueError(
            f"Invalid user_column '{user_column}': expected 'table.column' format."
        )
    table, column = user_column.split(".", 1)
    table, column = table.strip(), column.strip()
    if not table or not column:
        raise ValueError(
            f"Invalid user_column '{user_column}': expected 'table.column' format."
        )
    return table, column

def _is_not_matched(user_column: Any) -> bool:
    if user_column is None:
        return True
    if isinstance(user_column, str) and user_column.strip().lower() in _NOT_MATCHED_MARKERS:
        return True
    return False

def _split_language_and_entries(raw: Any) -> tuple[str, List[Dict[str, Any]]]:
    if isinstance(raw, list):
        return "en", raw
    if isinstance(raw, dict):
        language = raw.get("language", "en")
        entries = raw.get("columns")
        if not isinstance(entries, list):
            raise ValueError('Mapping object must have a "columns" array, e.g. {"language": "ar", "columns": [...]}.')
        return language, entries
    raise ValueError('Mapping must be a JSON array, or an object like {"language": "ar", "columns": [...]}.')

def build_mapping_from_entries(business_id: int, entries: List[Dict[str, Any]], language: str = "en") -> ColumnMapping:
    mapping: Dict[str, MappedColumn] = {}

    for entry in entries:
        ref = entry.get("our_schema")
        if not ref or ref not in CANONICAL_SCHEMA:
            continue

        user_column = entry.get("user_column")
        if _is_not_matched(user_column):
            continue

        table, column = _parse_user_column(str(user_column))
        user_label = entry.get("user_label") or _humanize(column)
        mapping[ref] = MappedColumn(table=table, column=column, user_label=user_label)

    return ColumnMapping(business_id=business_id, mapping=mapping, language=language)

_MAPPINGS_DIR = Path(__file__).parent / "data" / "business_mappings"

def get_business_mapping(business_id: int) -> ColumnMapping:
    path = _MAPPINGS_DIR / f"{business_id}.json"
    if not path.exists():
        return ColumnMapping(business_id=business_id, mapping={})

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    language, entries = _split_language_and_entries(raw)
    return build_mapping_from_entries(business_id, entries, language=language)

def save_business_mapping(business_id: int, raw: Any) -> Dict[str, Any]:
    language, entries = _split_language_and_entries(raw)

    unknown_refs = sorted({
        entry.get("our_schema") for entry in entries
        if isinstance(entry, dict) and entry.get("our_schema") not in CANONICAL_SCHEMA
    })

    mapping = build_mapping_from_entries(business_id, entries, language=language)

    _MAPPINGS_DIR.mkdir(parents=True, exist_ok=True)
    path = _MAPPINGS_DIR / f"{business_id}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

    matched_refs = sorted(mapping._mapping.keys())
    unmatched_refs = sorted(set(CANONICAL_SCHEMA) - set(matched_refs))

    return {
        "business_id": business_id,
        "language": mapping.language,
        "saved_to": str(path.relative_to(Path(__file__).parent.parent)),
        "matched_columns": len(matched_refs),
        "total_canonical_columns": len(CANONICAL_SCHEMA),
        "unmatched_columns": unmatched_refs,
        "unknown_our_schema_keys_ignored": unknown_refs,
    }