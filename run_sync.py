# run_sync.py

import asyncio
from datetime import datetime

# ← Change this import if your folder structure is different
from app.services.auto_sync import sync_all_users

print(f"[{datetime.now()}] Starting sync (cron job)")

asyncio.run(sync_all_users())

print(f"[{datetime.now()}] Sync finished successfully")