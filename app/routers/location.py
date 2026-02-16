from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.dependencies import get_citytag_client, get_current_user
from app.models.user import UserInDB
from app.services.citytag import CityTagClient, CityTagError


router = APIRouter(prefix="/api", tags=["location"])


@router.get("/location/{sn}")
async def get_latest_location(
    sn: str = Path(..., description="Device serial number"),
    current_user: Annotated[UserInDB, Depends(get_current_user)] = None,
    citytag: Annotated[CityTagClient, Depends(get_citytag_client)] = None,
) -> Dict[str, Any]:
    """
    Return the latest known location for a given device SN.
    """
    token = current_user.citytag_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CityTag token missing; please login again",
        )

    try:
        latest: Optional[Dict[str, Any]] = await citytag.get_latest_location(
            uid=current_user.uid,
            token=token,
            sn=sn,
        )
    except CityTagError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    if not latest:
        return {"sn": sn, "latest": None}

    return {"sn": sn, "latest": latest}

