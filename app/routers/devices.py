from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_citytag_client, get_current_user, get_mongo_service
from app.models.user import UserInDB
from app.services.citytag import CityTagClient, CityTagError
from app.services.mongodb import MongoService


router = APIRouter(prefix="/api", tags=["devices"])


@router.get("/devices")
async def list_devices(
    sn: str | None = Query(default=None, description="Optional device SN filter"),
    current_user: Annotated[UserInDB, Depends(get_current_user)] = None,
    citytag: Annotated[CityTagClient, Depends(get_citytag_client)] = None,
    mongo: Annotated[MongoService, Depends(get_mongo_service)] = None,
) -> List[Dict[str, Any]]:
    """
    Get all devices associated with the authenticated user.
    """
    token = current_user.citytag_token
    if not token:
        # If token missing, we cannot transparently re-login without password;
        # for prototype we expect login endpoint to have set this.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CityTag token missing; please login again",
        )

    try:
        devices = await citytag.get_devices(
            uid=current_user.uid,
            token=token,
            
        )
    except CityTagError as exc:
        # If token is invalid, instruct client to re-login
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    return devices

