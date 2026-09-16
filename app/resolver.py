from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from app import config
from app.catalog import WidgetDef, TableColumn, widgets_for_dashboards
from app.db import run_query
from app.mapping import ColumnMapping, MappedColumn

def _quoted(mapped: MappedColumn) -> str:
    return f"`{mapped.table}`.`{mapped.column}`"

_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_.]*)\}")

def _build_substitutions(mapping: ColumnMapping, required_columns: List[str]) -> Dict[str, str]:
    subs: Dict[str, str] = {}
    entities = set()
    for ref in required_columns:
        entity = ref.split(".")[0]
        entities.add(entity)
        mapped = mapping.get(ref)
        if mapped is not None:
            subs[ref] = _quoted(mapped)

    for entity in entities:
        table = mapping.table_for_entity(entity)
        if table:
            subs[f"{entity}.__table__"] = f"`{table}`"

    return subs

def _render_sql(template: str, subs: Dict[str, str]) -> str:
    def _replace(match: "re.Match[str]") -> str:
        key = match.group(1)
        if key not in subs:
            raise KeyError(f"Unresolvable placeholder in SQL template: {{{key}}}")
        return subs[key]

    return _PLACEHOLDER_RE.sub(_replace, template)

def _time_bucket_expr(mapped_time_col: str, granularity: str) -> str:
    if granularity == "week":
        return f"DATE(DATE_SUB({mapped_time_col}, INTERVAL WEEKDAY({mapped_time_col}) DAY))"
    if granularity == "month":
        return f"DATE_FORMAT({mapped_time_col}, '%Y-%m-01')"
    return f"DATE({mapped_time_col})"

def _date_filter_clause(mapped_time_col: str, start: Optional[date], end: Optional[date],
                         lifetime: bool = False) -> str:
    if lifetime or not start or not end:
        return ""
    return f"AND {mapped_time_col} BETWEEN '{start.isoformat()}' AND '{end.isoformat()}'"

def _resolve_date_range(start_date: Optional[date], end_date: Optional[date],
                         preset: Optional[str]) -> tuple[Optional[date], Optional[date]]:
    if preset == config.LIFETIME_PRESET:
        return None, None
    if start_date and end_date:
        return start_date, end_date
    if preset:
        days = config.DATE_PRESETS_TO_DAYS.get(preset)
        if days:
            end = date.today()
            start = end - timedelta(days=days)
            return start, end

    end = date.today()
    start = end - timedelta(days=config.DEFAULT_LOOKBACK_DAYS)
    return start, end

def _label_for(ref: Optional[str], mapping: ColumnMapping, fallback: str) -> str:
    if ref is None:
        return fallback
    mapped = mapping.get(ref)
    return mapped.user_label if mapped else fallback

def _title_for(widget: WidgetDef, mapping: ColumnMapping) -> str:
    if mapping.language == "ar" and widget.title_fallback_ar:
        return widget.title_fallback_ar
    return widget.title_fallback

def _build_sql(widget: WidgetDef, mapping: ColumnMapping, granularity: str,
               start_date: Optional[date], end_date: Optional[date], lifetime: bool = False) -> str:
    subs = _build_substitutions(mapping, widget.required_columns)

    if widget.chart_type == "line":
        assert widget.time_ref is not None, f"{widget.id}: line widgets must set time_ref"
        mapped_time_col = subs[widget.time_ref]
        subs["bucket_expr"] = _time_bucket_expr(mapped_time_col, granularity)
        subs["date_filter"] = _date_filter_clause(mapped_time_col, start_date, end_date, lifetime=lifetime)

    return _render_sql(widget.sql, subs)

def _resolve_widget(widget: WidgetDef, mapping: ColumnMapping, granularity: str,
                     start_date: Optional[date], end_date: Optional[date],
                     lifetime: bool = False) -> Optional[Dict[str, Any]]:
    if not mapping.has_all(widget.required_columns):
        return None

    sql = _build_sql(widget, mapping, granularity, start_date, end_date, lifetime=lifetime)
    rows = run_query(sql)
    title = _title_for(widget, mapping)

    if widget.chart_type == "kpi":
        value = rows[0]["value"] if rows else None
        return {
            "id": widget.id,
            "type": "kpi",
            "title": _label_for(widget.value_ref, mapping, title),
            "value": value,
        }

    if widget.chart_type in ("bar", "pie", "line"):

        x_source_ref = widget.time_ref if widget.chart_type == "line" else widget.x_ref
        x_label = _label_for(x_source_ref, mapping, title)
        y_label = _label_for(widget.y_ref, mapping, title)
        return {
            "id": widget.id,
            "type": widget.chart_type,
            "title": title,
            "x_axis": {"label": x_label, "data": [r["x"] for r in rows]},
            "y_axis": {"label": y_label, "data": [r["y"] for r in rows]},
        }

    if widget.chart_type == "table":
        columns_meta = []
        for col in (widget.table_columns or []):
            label = title if col.computed else _label_for(col.ref, mapping, col.label)
            columns_meta.append({"key": col.ref or col.label, "label": label})
        return {
            "id": widget.id,
            "type": "table",
            "title": title,
            "columns": columns_meta,
            "rows": rows,
        }

    raise ValueError(f"Unknown chart_type for widget {widget.id!r}: {widget.chart_type!r}")

def resolve_dashboards(
    mapping: ColumnMapping,
    dashboard_ids: List[str],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    granularity: str = config.DEFAULT_GRANULARITY,
    lifetime: bool = False,
) -> Dict[str, Any]:
    if lifetime:
        resolved_start, resolved_end = None, None
    else:
        resolved_start, resolved_end = _resolve_date_range(start_date, end_date, None)

    result: Dict[str, Any] = {}
    for dashboard_id in dashboard_ids:
        widgets = widgets_for_dashboards([dashboard_id])
        resolved_widgets = []
        for widget in widgets:
            resolved = _resolve_widget(widget, mapping, granularity, resolved_start, resolved_end, lifetime=lifetime)
            if resolved is not None:
                resolved_widgets.append(resolved)
        result[dashboard_id] = {"widgets": resolved_widgets}

    return result