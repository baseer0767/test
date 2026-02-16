from datetime import datetime, timedelta
import os
from typing import Annotated

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status

from app.models.user import UserInDB, UserPublic
from app.services.mongodb import MongoService
from app.services.citytag import CityTagClient
from app.services.location import LocationService


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))


def get_settings():
    return {
        "mongo_uri": os.getenv("MONGO_URI", "mongodb://localhost:27017/citytag_dashboard"),
        "citytag_base_url": os.getenv("CITYTAG_BASE_URL", "http://citytag.yuminstall.top"),
        "jwt_secret_key": os.getenv("JWT_SECRET_KEY", "change_this_secret_key"),
        "jwt_algorithm": os.getenv("JWT_ALGORITHM", "HS256"),
        "jwt_expire_minutes": int(os.getenv("JWT_EXPIRE_MINUTES", "1440")),
    }


def get_mongo_service() -> MongoService:
    settings = get_settings()
    return MongoService(settings["mongo_uri"])


def get_citytag_client() -> CityTagClient:
    settings = get_settings()
    return CityTagClient(settings["citytag_base_url"])


def create_access_token(subject: str) -> str:
    settings = get_settings()
    now = datetime.utcnow()
    expire = now + timedelta(minutes=settings["jwt_expire_minutes"])
    payload = {"sub": subject, "iat": now.timestamp(), "exp": expire.timestamp()}
    token = jwt.encode(payload, settings["jwt_secret_key"], algorithm=settings["jwt_algorithm"])
    return token


async def get_current_user(
    request: Request,
    mongo: Annotated[MongoService, Depends(get_mongo_service)],
) -> UserInDB:
    """
    Simple JWT-based auth dependency.
    Expects "Authorization: Bearer <token>" header from frontend.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    token = auth_header.split(" ", 1)[1].strip()
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings["jwt_secret_key"],
            algorithms=[settings["jwt_algorithm"]],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await mongo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def user_to_public(user: UserInDB) -> UserPublic:
    return UserPublic(
        id=str(user.id),
        email=user.email,
        uid=user.uid,
        created_at=user.created_at,
    )

def get_location_service(
    mongo: Annotated[MongoService, Depends(get_mongo_service)]
) -> LocationService:
    return LocationService(mongo.db)

