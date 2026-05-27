"""Structured slot updates from interview LLM / heuristics."""

from pydantic import BaseModel, Field

from app.schemas.architecture_spec import SlotStatus


class SlotUpdate(BaseModel):
    key: str
    value: str = ""
    status: SlotStatus = SlotStatus.EMPTY


class SlotExtractionResult(BaseModel):
    slot_updates: list[SlotUpdate] = Field(default_factory=list)
