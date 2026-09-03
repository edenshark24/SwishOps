from fastapi import FastAPI
import os

app = FastAPI(title="SwishOps Backend", version="1.0.0")

ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": ENVIRONMENT}

@app.get("/api/nba/stats")
async def get_nba_stats():
    return {
        "message": "Real-time NBA analytics pipeline active",
        "matchups": [
            {"home": "Boston Celtics", "away": "Denver Nuggets", "status": "Live"}
        ]
    }
