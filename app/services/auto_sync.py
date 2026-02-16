import asyncio
from datetime import datetime, timedelta
from httpx import HTTPStatusError

from app.dependencies import get_settings
from app.services.mongodb import MongoService
from app.services.citytag import CityTagClient, CityTagError
from app.routers.auth import login
from app.models.user import UserCreate

SYNC_INTERVAL_SECONDS = 600  # 1 minute


async def try_relogin(email: str, password: str, uid: str, mongo: MongoService, citytag: CityTagClient) -> str | None:
    """Attempt to re-login to CityTag and update the token in DB."""
    print(f"   ↻ Re-login attempt for {email} ...")
    try:
        payload = UserCreate(email=email, password=password, uid=uid)
        await login(payload=payload, mongo=mongo, citytag=citytag)

        user_doc = await mongo.users.find_one({"email": email})
        if user_doc and user_doc.get("citytag_token"):
            print(f"   ✓ Re-login successful → new token obtained")
            return user_doc["citytag_token"]

        print(f"   ✗ Login succeeded but token not found in DB")
        return None
    except Exception as exc:
        print(f"   ✗ Re-login failed for {email}: {exc}")
        return None


async def get_user_devices(citytag: CityTagClient, uid: str, token: str, email: str):
    """Fetch devices for a user. Returns None if token is invalid/expired."""
    try:
        devices = await citytag.get_devices(uid=uid, token=token)
        return devices
    except (CityTagError, HTTPStatusError) as e:
        msg = str(e).lower()
        if any(kw in msg for kw in ["token", "expired", "invalid token", "invalid", "401", "unauthorized", "400", "bad request"]):
            print(f"   ⚠ Token invalid/expired ({e}) for {email} → re-login triggered")
            return None
        print(f"❌ Non-auth error fetching devices for {email}: {e}")
        return []


async def sync_all_users() -> None:
    """Sync location history for all users and devices, with automatic re-login."""
    settings = get_settings()
    mongo = MongoService(settings["mongo_uri"])
    citytag = CityTagClient(settings["citytag_base_url"])

    print("\n🔄 ===== AUTO SYNC STARTED =====")

    total_users = total_devices = total_points = re_logins = 0

    async for user in mongo.users.find({}):
        total_users += 1
        email, password, uid, token = user.get("email"), user.get("password"), user.get("uid"), user.get("citytag_token")
        if not all([email, password, uid]):
            print(f"⚠ Skipping user — missing email/password/uid")
            continue

        current_token = token
        devices = await get_user_devices(citytag, uid, current_token, email) if current_token else None
        if devices is None:
            new_token = await try_relogin(email, password, uid, mongo, citytag)
            if new_token:
                current_token, re_logins = new_token, re_logins + 1
                devices = await get_user_devices(citytag, uid, current_token, email)
                if devices is None:
                    print(f"   ✗ Failed to get devices even after re-login for {email}")
                    continue
            else:
                print(f"   ✗ Re-login failed for {email} — skipping this user")
                continue

        if not devices:
            print(f"   ⚠ No devices found for {email} after all attempts")
            continue

        total_devices += len(devices)
        start_time, end_time = datetime.utcnow() - timedelta(minutes=15), datetime.utcnow()

        for device in devices:
            sn = device.get("sn")
            if not sn:
                continue

            try:
                history = await citytag.get_location_history(uid=uid, token=current_token, sn=sn, start_time=start_time, end_time=end_time)
            except (CityTagError, HTTPStatusError) as e:
                print(f"❌ History fetch failed for SN={sn} ({email}): {e}")
                continue

            inserted_this_device = 0
            for item in history:
                if await mongo.upsert_location_from_citytag(history_item=item, uid=uid, sn=sn):
                    inserted_this_device += 1
                    total_points += 1

            if inserted_this_device:
                print(f"   + {inserted_this_device} new points for SN={sn}")

    print("✅ ===== AUTO SYNC COMPLETED =====")
    print(f"👥 Users processed:       {total_users:3d}")
    print(f"🔑 Successful re-logins:   {re_logins:3d}")
    print(f"📱 Devices processed:      {total_devices:3d}")
    print(f"📍 Points inserted/updated: {total_points:3d}")
    print("====================================\n")


async def scheduler_loop() -> None:
    await sync_all_users()
    while True:
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
        await sync_all_users()


def start_auto_sync_tasks(app):
    @app.on_event("startup")
    async def start_scheduler():
        print("🚀 Starting Auto Sync Scheduler...")
        asyncio.create_task(scheduler_loop())
