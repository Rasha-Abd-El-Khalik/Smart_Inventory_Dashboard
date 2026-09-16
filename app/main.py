from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from starlette.concurrency import run_in_threadpool

from app import config
from app.catalog import DASHBOARD_IDS
from app.mapping import get_business_mapping, save_business_mapping
from app.resolver import resolve_dashboards
from app.schemas import DashboardResponse

app = FastAPI(
    title="Smart Inventory Dashboard API",
    description="Config-driven, per-business dashboard resolver.",
    version="1.0.0",
)

def _parse_dashboard_param(dashboard: Optional[List[str]]) -> List[str]:
    if not dashboard:
        return list(DASHBOARD_IDS)

    requested: List[str] = []
    for raw in dashboard:
        requested.extend([part.strip() for part in raw.split(",") if part.strip()])

    unknown = [d for d in requested if d not in DASHBOARD_IDS]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown dashboard(s): {unknown}. Valid values: {DASHBOARD_IDS}",
        )

    seen = set()
    ordered_unique = []
    for d in requested:
        if d not in seen:
            seen.add(d)
            ordered_unique.append(d)
    return ordered_unique

@app.get("/businesses/{business_id}/dashboard", response_model=DashboardResponse)
def get_dashboard(
    business_id: int,
    dashboard: Optional[List[str]] = Query(
        default=None,
        description="One or more dashboard ids (repeat the param or comma-separate). "
                    "Omit to get all dashboards.",
    ),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    preset: Optional[str] = Query(
        default=None,
        description=f"One of: {list(config.ALL_PRESETS)}",
    ),
    granularity: str = Query(default=config.DEFAULT_GRANULARITY),
):
    if granularity not in config.ALLOWED_GRANULARITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid granularity '{granularity}'. Allowed: {config.ALLOWED_GRANULARITIES}",
        )
    if preset and preset not in config.ALL_PRESETS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid preset '{preset}'. Allowed: {list(config.ALL_PRESETS)}",
        )
    if bool(start_date) != bool(end_date):
        raise HTTPException(status_code=400, detail="start_date and end_date must be provided together.")

    dashboard_ids = _parse_dashboard_param(dashboard)
    mapping = get_business_mapping(business_id)

    lifetime = preset == config.LIFETIME_PRESET

    resolved_start = start_date
    resolved_end = end_date
    if not resolved_start and preset and not lifetime:
        days = config.DATE_PRESETS_TO_DAYS[preset]
        resolved_end = date.today()
        resolved_start = resolved_end - timedelta(days=days)

    dashboards = resolve_dashboards(
        mapping=mapping,
        dashboard_ids=dashboard_ids,
        start_date=resolved_start,
        end_date=resolved_end,
        granularity=granularity,
        lifetime=lifetime,
    )

    return DashboardResponse(
        business_id=business_id,
        dashboards=dashboards,
        generated_at=datetime.utcnow(),
    )

@app.post("/businesses/{business_id}/mapping")
async def upload_business_mapping(
    business_id: int,
    file: UploadFile = File(..., description="The mapping JSON file (array of {our_schema, user_column}) for this business."),
):
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="File must be a .json file.")

    raw_bytes = await file.read()
    try:
        entries = json.loads(raw_bytes)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}")

    try:
        summary = save_business_mapping(business_id, entries)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return summary

@app.websocket("/businesses/{business_id}/dashboard/ws")
async def dashboard_ws(websocket: WebSocket, business_id: int):
    await websocket.accept()
    params = websocket.query_params

    try:
        dashboard_ids = _parse_dashboard_param(params.getlist("dashboard") or None)

        granularity = params.get("granularity", config.DEFAULT_GRANULARITY)
        if granularity not in config.ALLOWED_GRANULARITIES:
            raise HTTPException(status_code=400, detail=f"Invalid granularity '{granularity}'.")

        preset = params.get("preset")
        if preset and preset not in config.ALL_PRESETS:
            raise HTTPException(status_code=400, detail=f"Invalid preset '{preset}'.")

        start_date_raw = params.get("start_date")
        end_date_raw = params.get("end_date")
        start_date = date.fromisoformat(start_date_raw) if start_date_raw else None
        end_date = date.fromisoformat(end_date_raw) if end_date_raw else None
        if bool(start_date) != bool(end_date):
            raise HTTPException(status_code=400, detail="start_date and end_date must be provided together.")

        lifetime = preset == config.LIFETIME_PRESET
        resolved_start = start_date
        resolved_end = end_date
        if not resolved_start and preset and not lifetime:
            days = config.DATE_PRESETS_TO_DAYS[preset]
            resolved_end = date.today()
            resolved_start = resolved_end - timedelta(days=days)
    except (HTTPException, ValueError) as exc:
        detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
        await websocket.send_json({"error": detail})
        await websocket.close(code=1008)
        return

    try:
        while True:

            mapping = get_business_mapping(business_id)

            dashboards = await run_in_threadpool(
                resolve_dashboards,
                mapping=mapping,
                dashboard_ids=dashboard_ids,
                start_date=resolved_start,
                end_date=resolved_end,
                granularity=granularity,
                lifetime=lifetime,
            )

            await websocket.send_json(jsonable_encoder({
                "business_id": business_id,
                "dashboards": dashboards,
                "generated_at": datetime.utcnow(),
            }))

            await asyncio.sleep(config.WS_REFRESH_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        pass

@app.get("/health")
def health():
    return {"status": "ok"}
