# app/routers/sync.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated

from app.dependencies import get_current_user, get_citytag_client, get_mongo_service
from app.models.user import UserInDB
from app.services.citytag import CityTagClient, CityTagError
from app.services.mongodb import MongoService


router = APIRouter(prefix="/api", tags=["sync"])


@router.post("/sync/locations")
async def sync_device_locations(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    citytag: Annotated[CityTagClient, Depends(get_citytag_client)],
    mongo: Annotated[MongoService, Depends(get_mongo_service)],
):
    """
    Fetch recent location history from CityTag for the current user's devices
    and store it in our MongoDB (for trajectory & playback).
    """
    if not current_user.citytag_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "CityTag token missing")

    # Get all devices for this user
    try:
        devices = await citytag.get_devices(
            uid=current_user.uid,
            token=current_user.citytag_token,
        )
    except CityTagError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e))

    if not devices:
        return {"message": "No devices found", "inserted": 0}

    inserted_count = 0
    from datetime import datetime, timedelta
    start_time = datetime.utcnow() - timedelta(days=10)  # last 3 days - adjust as needed

    for device in devices:
        sn = device.get("sn")
        if not sn:
            continue

        try:
            history = await citytag.get_location_history(  # ← you need this method!
                uid=current_user.uid,
                token=current_user.citytag_token,
                sn=sn,
                start_time=start_time,
                end_time=datetime.utcnow(),
            )
        except CityTagError:
            continue

        for item in history:
            inserted = await mongo.upsert_location_from_citytag(
                history_item=item,
                uid=current_user.uid,
                sn=sn,
            )
            if inserted:
                inserted_count += 1

    return {
        "devices_found": len(devices),
        "points_inserted": inserted_count,
        "message": "Sync completed"
    }