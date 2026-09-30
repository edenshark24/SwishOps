from datetime import datetime, timezone
import logging
import os
import threading

from fastapi import Depends, FastAPI, HTTPException
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="SwishOps Backend", version="1.0.0")
# Expose Prometheus metrics; keep probe and scrape traffic out of the request metrics.
Instrumentator(excluded_handlers=["^/metrics$", "^/health$"]).instrument(app).expose(app, endpoint="/metrics")

ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "1"))
DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))

logging.basicConfig(level=LOG_LEVEL.upper())
logger = logging.getLogger("swishops.backend")

TREND_COLUMNS = """
    player_id, player_name, team, position,
    season_avg_pts, last5_avg_pts,
    season_avg_reb, last5_avg_reb,
    season_avg_ast, last5_avg_ast,
    trend_direction, trend_magnitude,
    minutes_avg, minutes_last_game,
    rest_flag, games_played, updated_at
"""

# ── Connection pool ──────────────────────────────────────────────────────────
# The pool is created lazily on first use so the app (and its tests) can start
# without a reachable database. SimpleConnectionPool is not thread-safe, and
# sync endpoints run in FastAPI's threadpool, so all pool access is locked.
_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = pool.SimpleConnectionPool(
                DB_POOL_MIN,
                DB_POOL_MAX,
                host=DB_HOST,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT,
                connect_timeout=5,
            )
        return _pool


def get_db():
    """FastAPI dependency: borrow a connection and always return it to the pool."""
    try:
        db_pool = _get_pool()
        with _pool_lock:
            conn = db_pool.getconn()
    except (psycopg2.OperationalError, pool.PoolError) as exc:
        logger.error("Database unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable")

    broken = False
    try:
        yield conn
    except psycopg2.OperationalError as exc:
        broken = True
        logger.error("Database connection error: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable")
    finally:
        if not broken and conn.closed == 0:
            conn.rollback()  # read-only requests; end any open transaction
        with _pool_lock:
            db_pool.putconn(conn, close=broken or conn.closed != 0)


def fetch_all(conn, query, params=None):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return cur.fetchall()


def fetch_one(conn, query, params=None):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return cur.fetchone()


@app.on_event("shutdown")
def close_pool():
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.closeall()
            _pool = None


# ── Endpoints ────────────────────────────────────────────────────────────────
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


@app.get("/api/trends/up")
def get_trends_up(conn=Depends(get_db)):
    return fetch_all(
        conn,
        f"SELECT {TREND_COLUMNS} FROM player_trends "
        "WHERE trend_direction = 'UP' "
        "ORDER BY trend_magnitude DESC;",
    )


@app.get("/api/trends/down")
def get_trends_down(conn=Depends(get_db)):
    return fetch_all(
        conn,
        f"SELECT {TREND_COLUMNS} FROM player_trends "
        "WHERE trend_direction = 'DOWN' "
        "ORDER BY trend_magnitude ASC;",
    )


@app.get("/api/trends/risers")
def get_trend_risers(conn=Depends(get_db)):
    return fetch_all(
        conn,
        f"SELECT {TREND_COLUMNS} FROM player_trends "
        "WHERE trend_magnitude IS NOT NULL "
        "ORDER BY trend_magnitude DESC LIMIT 10;",
    )


@app.get("/api/players/{player_id}")
def get_player(player_id: int, conn=Depends(get_db)):
    trend = fetch_one(
        conn,
        f"SELECT {TREND_COLUMNS} FROM player_trends WHERE player_id = %s;",
        (player_id,),
    )
    if trend is None:
        raise HTTPException(status_code=404, detail="Player not found")

    recent_games = fetch_all(
        conn,
        """
        SELECT game_id, game_date, team, points, rebounds, assists,
               steals, blocks, minutes, plus_minus
        FROM player_stats
        WHERE player_id = %s
        ORDER BY game_date DESC
        LIMIT 10;
        """,
        (player_id,),
    )
    return {"player": trend, "recent_games": recent_games}


@app.get("/api/games/today")
def get_games_today(conn=Depends(get_db)):
    # The Lambda ingests games using the UTC date, so match that here.
    today = datetime.now(timezone.utc).date()
    games = fetch_all(
        conn,
        """
        SELECT game_id, home_team, away_team, home_score, away_score,
               status, game_date, updated_at
        FROM nba_games
        WHERE game_date = %s
        ORDER BY game_id;
        """,
        (today,),
    )
    return {"date": today.isoformat(), "games": games}
