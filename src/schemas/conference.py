from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class CoreRank(str, Enum):
    A_STAR = "A*"
    A = "A"
    B = "B"
    C = "C"
    UNRANKED = "Unranked"


class ConferenceFormat(str, Enum):
    IN_PERSON = "in-person"
    VIRTUAL = "virtual"
    HYBRID = "hybrid"


class Coordinates(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class ConferenceLocation(BaseModel):
    city: str
    country: str
    continent: Optional[str] = None
    coordinates: Optional[Coordinates] = None


class ConferenceDates(BaseModel):
    start: date
    end: Optional[date] = None
    submission_deadline: Optional[date] = None
    notification_date: Optional[date] = None
    camera_ready_deadline: Optional[date] = None


class DecisionResult(BaseModel):
    valid: bool
    relevant: bool
    reason: str


class ConferenceScores(BaseModel):
    distance: Optional[float] = Field(None, ge=0, le=100)
    relevancy: Optional[float] = Field(None, ge=0, le=100)
    prestige: Optional[float] = Field(None, ge=0, le=100)
    total: Optional[float] = Field(None, ge=0, le=100)


class Conference(BaseModel):
    id: str = Field(description="Stable hash of name + year, used for deduplication")
    name: str = Field(description="Full conference name")
    acronym: Optional[str] = Field(None, description="Short name, e.g. 'ICML'")
    year: int

    url: Optional[HttpUrl] = Field(None, description="Official conference website")
    source_url: str = Field(description="URL the data was scraped from")
    scraped_at: datetime = Field(description="When this record was fetched")

    dates: ConferenceDates
    location: Optional[ConferenceLocation] = None
    format: ConferenceFormat = ConferenceFormat.IN_PERSON

    topics: list[str] = Field(default_factory=list, description="Research area keywords")
    description: Optional[str] = Field(None, description="Short summary of the conference scope")

    core_rank: Optional[CoreRank] = None

    decision: Optional[DecisionResult] = None
    decision_pre_validation: Optional[DecisionResult] = Field(
        None,
        description="Decision agent's raw output before the self-validation pass overrides it "
        "(only set when decide() is called with self_validate=True; lets the benchmark measure "
        "how often self-validation actually changes the outcome).",
    )
    scores: Optional[ConferenceScores] = None


class UserPreferences(BaseModel):
    address: str = Field(description="Home or university address used for distance scoring")
    coordinates: Optional[Coordinates] = Field(None, description="Resolved from address")
    research_title: str = Field(description="Title of the candidate's research topic")
    research_context: str = Field(description="Brief description of the research work")
