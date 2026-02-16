from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.dependencies import (
    create_access_token,
    get_citytag_client,
    get_mongo_service,
    user_to_public,
)
from app.models.user import UserCreate, UserPublic
from app.services.citytag import CityTagClient, CityTagError
from app.services.mongodb import MongoService


router = APIRouter(prefix="/api", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    uid: str


class LoginResponse(BaseModel):
    user: UserPublic
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    mongo: Annotated[MongoService, Depends(get_mongo_service)],
    citytag: Annotated[CityTagClient, Depends(get_citytag_client)],
):
    """
    Login endpoint.

    - Logs into CityTag using email + password (treated as username/password)
    - Stores/updates user in MongoDB
    - Returns JWT access token for subsequent authenticated calls
    """
    try:
        citytag_data = await citytag.login(username=payload.email, password=payload.password)
    except CityTagError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    token = citytag_data.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="CityTag did not return a token",
        )

    user_data = UserCreate(
        email=payload.email,
        password=payload.password,
        uid=payload.uid,
    )
    user = await mongo.create_or_update_user(user_data, citytag_token=token)

    access_token = create_access_token(str(user.id))

    return LoginResponse(
        user=user_to_public(user),
        access_token=access_token,
    )

