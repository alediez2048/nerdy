# Ad-Ops-Autopilot — Curation schemas (PA-10)
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CuratedSetCreate(BaseModel):
    name: str = "Default Set"


class CuratedAdAdd(BaseModel):
    ad_id: str
    position: int = 0


class CuratedAdUpdate(BaseModel):
    position: int | None = None
    annotation: str | None = None
    edited_copy: dict[str, Any] | None = None


class BatchReorder(BaseModel):
    ad_ids: list[str]


class CuratedAdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ad_id: str
    position: int
    annotation: str | None = None
    edited_copy: dict[str, Any] | None = None
    created_at: datetime


class CuratedSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    name: str
    created_at: datetime
    updated_at: datetime | None = None
    ads: list[CuratedAdResponse] = []
