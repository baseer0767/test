from typing import Optional
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId

from app.models.user import UserInDB, UserCreate


MONGO_DB_NAME = "citytag_dashboard"
USERS_COLLECTION = "users"


class MongoService:
    def __init__(self, uri: str):
        self._client = AsyncIOMotorClient(uri)

    @property
    def client(self) -> AsyncIOMotorClient:
        return self._client

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._client[MONGO_DB_NAME]

    @property
    def users(self):
        return self.db[USERS_COLLECTION]

    @property
    def locations(self):
        return self.db["locations"]

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        doc = await self.users.find_one({"email": email})
        if not doc:
            return None
        return UserInDB(**doc)

    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None

        doc = await self.users.find_one({"_id": oid})
        if not doc:
            return None

        return UserInDB(**doc)

    async def create_or_update_user(
        self,
        data: UserCreate,
        citytag_token: Optional[str] = None,
    ) -> UserInDB:
        existing = await self.get_user_by_email(data.email)

        payload = {
            "email": data.email,
            "password": data.password,
            "uid": data.uid,
        }
        if citytag_token is not None:
            payload["citytag_token"] = citytag_token

        if existing:
            await self.users.update_one(
                {"_id": existing.id},
                {"$set": payload},
            )
            updated = await self.users.find_one({"_id": existing.id})
            return UserInDB(**updated)

        result = await self.users.insert_one(payload)
        created = await self.users.find_one({"_id": result.inserted_id})
        return UserInDB(**created)

    async def update_user_token(self, user_id: str, token: str) -> None:
        await self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"citytag_token": token}},
        )

    async def upsert_location_from_citytag(
        self,
        history_item: dict,
        uid: str,
        sn: Optional[str] = None,
    ) -> bool:
        ts_raw = (
            history_item.get("gpstime")
            or history_item.get("time")
            or history_item.get("timestamp")
        )
        timestamp = self._parse_citytag_timestamp(ts_raw)

        doc = {
            "uid": uid,
            "sn": sn or history_item.get("sn"),
            "timestamp": timestamp,
            "lat": float(history_item.get("lat") or history_item.get("latitude") or 0),
            "lng": float(history_item.get("lng") or history_item.get("lon") or history_item.get("longitude") or 0),
        }

        if doc["lat"] == 0 or doc["lng"] == 0 or not doc["sn"]:
            return False

        query = {
            "uid": doc["uid"],
            "sn": doc["sn"],
            "timestamp": doc["timestamp"],
        }

        result = await self.locations.update_one(
            query,
            {"$set": doc},
            upsert=True,
        )

        return bool(result.upserted_id or result.modified_count > 0)

    def _parse_citytag_timestamp(self, value) -> datetime:
        if isinstance(value, (int, float)):
            if value > 1e10:
                return datetime.utcfromtimestamp(value / 1000)
            return datetime.utcfromtimestamp(value)

        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                pass

        return datetime.utcnow()  # fallback