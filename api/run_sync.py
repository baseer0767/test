# api/run_sync.py

import asyncio
from datetime import datetime

from app.services.auto_sync import sync_all_users

def handler(event, context):
    """
    Vercel serverless function – triggered by cron every 10 minutes.
    Runs the full sync job once per call.
    """
    start = datetime.utcnow()
    print(f"[{start.isoformat()}] Cron job triggered – starting sync")

    try:
        asyncio.run(sync_all_users())
    except Exception as e:
        print(f"Sync failed: {e}")
        return {
            "statusCode": 500,
            "body": f"Sync error: {str(e)}"
        }

    end = datetime.utcnow()
    duration = (end - start).total_seconds()
    print(f"[{end.isoformat()}] Sync completed in {duration:.1f} seconds")

    return {
        "statusCode": 200,
        "body": "Sync job completed"
    }