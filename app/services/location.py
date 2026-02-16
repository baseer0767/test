# app/services/location.py
from datetime import datetime
from typing import Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.models.location import LocationPointDB, TrajectoryResponse, PlaybackResponse


class LocationService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["locations"]

    async def get_trajectory(
        self,
        uid: str,
        sn: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[TrajectoryResponse]:
        cursor = self.collection.find(
            {
                "uid": uid,
                "sn": sn,
                "timestamp": {"$gte": start_time, "$lte": end_time},
            },
            {"lat": 1, "lng": 1, "timestamp": 1},
            sort=[("timestamp", 1)],
        )

        points = []
        async for doc in cursor:
            points.append([doc["lng"], doc["lat"]])  # GeoJSON: [lng, lat]

        if not points:
            return None

        return TrajectoryResponse(
            feature={
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": points},
                "properties": {
                    "device_sn": sn,
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                },
            },
            count=len(points),
            start_time=start_time,
            end_time=end_time,
            device_sn=sn,
        )

    async def get_playback_points(
        self,
        uid: str,
        sn: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[PlaybackResponse]:
        cursor = self.collection.find(
            {
                "uid": uid,
                "sn": sn,
                "timestamp": {"$gte": start_time, "$lte": end_time},
            },
            {"lat": 1, "lng": 1, "timestamp": 1, "speed": 1, "accuracy": 1},
            sort=[("timestamp", 1)],
        )

        points = []
        async for doc in cursor:
            points.append({
                "lat": doc["lat"],
                "lng": doc["lng"],
                "timestamp": doc["timestamp"],
            })

        if not points:
            return None

        duration = (end_time - start_time).total_seconds() if points else None

        return PlaybackResponse(
            points=points,
            count=len(points),
            start_time=start_time,
            end_time=end_time,
            device_sn=sn,
            duration_seconds=duration,
        )