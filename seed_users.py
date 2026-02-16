# seed_data.py
import asyncio
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


DB_NAME = "citytag_dashboard"


SEED_USERS = [
    {
        "email": "walishajeeh66@gmail.com",
        "password": "Trakker123",
        "uid": "251527",
    },
    {
        "email": "palhaxmat@gmail.com",
        "password": "@Zmat123",
        "uid": "251800",
    },
]


async def main() -> None:
    here = os.path.dirname(__file__)
    load_dotenv(dotenv_path=os.path.join(here, ".env"))

    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/citytag_dashboard")
    client = AsyncIOMotorClient(mongo_uri)
    db = client[DB_NAME]

    # ────────────────────────────────────────────────
    # Seed users collection
    # ────────────────────────────────────────────────

    users = db["users"]
    print("Seeding users...")

    now = datetime.now(timezone.utc)
    upserted = 0
    matched = 0

    for u in SEED_USERS:
        result = await users.update_one(
            {"email": u["email"]},
            {
                "$setOnInsert": {"email": u["email"], "created_at": now},
                "$set": {"password": u["password"], "uid": u["uid"]},
            },
            upsert=True,
        )
        matched += int(result.matched_count or 0)
        upserted += 1 if result.upserted_id else 0

    total_users = await users.count_documents({})
    print(f"Users seed complete. upserted={upserted} matched_existing={matched} total_users={total_users}")

    # ────────────────────────────────────────────────
    # Create / ensure locations collection + indexes
    # ────────────────────────────────────────────────

    locations = db["locations"]
    print("\nEnsuring indexes on locations collection...")

    # Primary index: fast queries by user + device + time range
    await locations.create_index(
        [("uid", 1), ("sn", 1), ("timestamp", 1)],
        name="uid_sn_timestamp_asc",
        background=True
    )

    # Optional: fast sort by most recent first
    await locations.create_index(
        [("timestamp", -1)],
        name="timestamp_desc",
        background=True
    )

    print("Indexes created (or already exist):")
    indexes = await locations.index_information()
    for name, info in indexes.items():
        print(f"  - {name}: {info['key']}")

    # ────────────────────────────────────────────────
    # Insert a few dummy location records (for quick testing)
    # You can comment this block out after the first run
    # ────────────────────────────────────────────────

    print("\nInserting 3 dummy location records (for testing trajectory/playback)...")

    dummy_data = [
        {
            "uid": "251527",
            "sn": "TEST_DEV_001",
            "timestamp": now - timedelta(hours=2),
            "lat": 24.8607,
            "lng": 67.0012
        },
        {
            "uid": "251527",
            "sn": "TEST_DEV_001",
            "timestamp": now - timedelta(hours=1, minutes=30),
            "lat": 24.8615,
            "lng": 67.0028
        },
        {
            "uid": "251800",
            "sn": "TEST_DEV_002",
            "timestamp": now - timedelta(hours=3),
            "lat": 24.8580,
            "lng": 66.9985
        }
    ]

    await locations.insert_many(dummy_data)
    print(f"Inserted {len(dummy_data)} dummy records")

    total_locations = await locations.count_documents({})
    print(f"Total documents in locations now: {total_locations}")

    # Quick preview of inserted data
    recent = await locations.find().sort("timestamp", -1).limit(3).to_list(3)
    print("\nMost recent 3 dummy points:")
    for doc in recent:
        print(f"  - {doc['timestamp']} | uid={doc['uid']} | sn={doc['sn']} | lat={doc['lat']}, lng={doc['lng']}")

    client.close()
    print("\nSeed & index creation complete.")


if __name__ == "__main__":
    asyncio.run(main())