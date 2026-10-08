"""Request schema for an incoming emergency signal.

Matches the message the Android app / relay sends. Field constraints
reject malformed signals before they reach the store.
"""

from pydantic import BaseModel, Field


class EmergencyRequest(BaseModel):
    message_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    emergency_code: int = Field(ge=1, le=7)
    severity: int = Field(ge=1, le=5)
    timestamp: int

    origin_lat: float | None = None
    origin_lon: float | None = None

    location_source: int = 0  # 0 UNKNOWN, 1 ORIGIN (exact), 2 RELAY_APPROXIMATE

    fallback_lat: float | None = None
    fallback_lon: float | None = None

    ttl: int = Field(ge=0)
    hop_count: int = Field(ge=0)
