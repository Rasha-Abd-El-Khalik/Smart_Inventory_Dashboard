from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

class AxisData(BaseModel):
    label: str
    data: List[Any]

class Widget(BaseModel):
    id: str
    type: str
    title: str

    value: Optional[Any] = None

    x_axis: Optional[AxisData] = None
    y_axis: Optional[AxisData] = None

    columns: Optional[List[Dict[str, str]]] = None
    rows: Optional[List[Dict[str, Any]]] = None

class DashboardBlock(BaseModel):
    widgets: List[Widget]

class DashboardResponse(BaseModel):
    business_id: int
    dashboards: Dict[str, DashboardBlock]
    generated_at: datetime
