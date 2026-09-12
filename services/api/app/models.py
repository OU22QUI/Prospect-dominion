from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class Account(BaseModel):
    id: str = Field(..., description="Canonical account id")
    domain: str
    legal_name: Optional[str] = None
    display_name: Optional[str] = None
    industry: Optional[str] = None
    icp_score: Optional[float] = None
    enrichment: dict[str, Any] = Field(default_factory=dict)


class Person(BaseModel):
    id: str = Field(..., description="Canonical person id")
    account_id: Optional[str] = None
    full_name: Optional[str] = None
    title: Optional[str] = None
    seniority: Optional[str] = None
    role_function: Optional[str] = None
    linkedin_url: Optional[str] = None
    psychographics: dict[str, Any] = Field(default_factory=dict)


class Thread(BaseModel):
    thread_id: str
    person_id: str
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    opp_stage: str = "new"
    consent_basis: str = "none"
    next_action_at: Optional[datetime] = None
    last_touch_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThreadCreateRequest(BaseModel):
    person_id: str
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    opp_stage: str = "new"
    consent_basis: str = "none"
    next_action_at: Optional[datetime] = None


class EventRecord(BaseModel):
    event_id: str
    thread_id: str
    event_type: str
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EventCreateRequest(BaseModel):
    thread_id: str
    event_type: str
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)


class OutcomeRecord(BaseModel):
    outcome_id: str
    thread_id: str
    account_id: Optional[str] = None
    stage_from: Optional[str] = None
    stage_to: str
    reason: Optional[str] = None
    value_amount: Optional[float] = None
    attributed_signal: Optional[str] = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OutcomeCreateRequest(BaseModel):
    thread_id: str
    account_id: Optional[str] = None
    stage_from: Optional[str] = None
    stage_to: str
    reason: Optional[str] = None
    value_amount: Optional[float] = None
    attributed_signal: Optional[str] = None
