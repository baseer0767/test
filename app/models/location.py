# app/models/location.py
from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field

# Import PyObjectId from user.py (or copy-paste if you prefer)
from app.models.user import PyObjectId


class LocationPointDB(BaseModel):
    """Internal representation of one location document in MongoDB"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    uid: str
    sn: str                           # device serial number
    timestamp: datetime
    lat: float
    lng: float

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat(),
        },
    )



# ────────────────────────────────────────────────
#               API Response Models
# ────────────────────────────────────────────────

class TrajectoryGeometry(BaseModel):
    type: str = "LineString"
    coordinates: List[List[float]]  # [[lng, lat], [lng, lat], ...]


class TrajectoryFeature(BaseModel):
    type: str = "Feature"
    geometry: TrajectoryGeometry
    properties: dict = Field(default_factory=dict)


class TrajectoryResponse(BaseModel):
    """GeoJSON-compatible response for drawing route line"""
    feature: TrajectoryFeature
    count: int
    start_time: datetime
    end_time: datetime
    device_sn: str

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )


class PlaybackPoint(BaseModel):
    lat: float
    lng: float
    timestamp: datetime


class PlaybackResponse(BaseModel):
    """Time-ordered points for animation/playback"""
    points: List[PlaybackPoint]
    count: int
    start_time: datetime
    end_time: datetime
    device_sn: str
    duration_seconds: Optional[float] = None

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )