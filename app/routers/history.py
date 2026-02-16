# app/routers/history.py
from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_current_user, get_location_service
from app.models.user import UserInDB
from app.models.location import TrajectoryResponse, PlaybackResponse
from app.services.location import LocationService


router = APIRouter(prefix="/api", tags=["history"])


@router.get("/devices/{sn}/trajectory", response_model=TrajectoryResponse)
async def get_device_trajectory(
    sn: str,
    start: Annotated[datetime, Query(...)],
    end: Annotated[datetime, Query(...)],
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    service: Annotated[LocationService, Depends(get_location_service)],
):
    """
    Get GeoJSON LineString for drawing the route on a map
    """
    if start >= end:
        raise HTTPException(400, "start must be before end")

    result = await service.get_trajectory(
        uid=current_user.uid,
        sn=sn,
        start_time=start,
        end_time=end,
    )

    if not result:
        raise HTTPException(404, "No location data found in time range")

    return result


@router.get("/devices/{sn}/playback", response_model=PlaybackResponse)
async def get_device_playback(
    sn: str,
    start: Annotated[datetime, Query(...)],
    end: Annotated[datetime, Query(...)],
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    service: Annotated[LocationService, Depends(get_location_service)],
):
    """
    Get time-ordered points suitable for animation / playback
    """
    if start >= end:
        raise HTTPException(400, "start must be before end")

    result = await service.get_playback_points(
        uid=current_user.uid,
        sn=sn,
        start_time=start,
        end_time=end,
    )

    if not result:
        raise HTTPException(404, "No location data found in time range")

    return result