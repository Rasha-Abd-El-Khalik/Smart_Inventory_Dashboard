from __future__ import annotations

import os
from typing import Any, Dict, List, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL

DB_USER = os.getenv("DB_USER", "avnadmin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "smart-inventory-dashboard-smart-inventory-dashboard-trail.h.aivencloud.com")
DB_PORT = os.getenv("DB_PORT", "19444")
DB_NAME = os.getenv("DB_NAME", "Aiven Cloud")

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
)

_engine: Engine | None = None

def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine

def run_query(sql: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        columns: Sequence[str] = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]
