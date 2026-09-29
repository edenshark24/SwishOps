import os
import json
import boto3
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# ── Environment variables ────────────────────────────────────────────────────
DB_HOST               = os.getenv("DB_HOST", "swishops-postgres-rds.c123456.us-east-1.rds.amazonaws.com")
DB_NAME               = os.getenv("DB_NAME", "swishops")
DB_USER               = os.getenv("DB_USER", "dbadmin")
DB_PORT               = os.getenv("DB_PORT", "5432")
DB_PASSWORD_SECRET_ARN = os.getenv("DB_PASSWORD_SECRET_ARN")
NBA_API_KEY_SECRET_ARN = os.getenv("NBA_API_KEY_SECRET_ARN")

NBA_BASE_URL          = "https://api.balldontlie.io/v1"

# ── Secrets Manager ──────────────────────────────────────────────────────────
def get_secret(secret_arn):
    """Retrieve a secret from AWS Secrets Manager."""
    if not secret_arn:
        return None
    client = boto3.session.Session().client(service_name="secretsmanager")
    try:
        response = client.get_secret_value(SecretId=secret_arn)
        secret = response.get("SecretString", "{}")
        try:
            return json.loads(secret)
        except json.JSONDecodeError:
            return secret
    except ClientError as e:
        print(f"❌ Error retrieving secret {secret_arn}: {e}")
        raise

# ── Database helpers ─────────────────────────────────────────────────────────
def get_db_connection(password):
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME,
        user=DB_USER, password=password, port=DB_PORT
    )

def create_tables(cursor):
    """Create all required tables if they don't exist."""

    # Existing games table (unchanged)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nba_games (
            id          SERIAL PRIMARY KEY,
            game_id     INT UNIQUE,
            home_team   VARCHAR(50),
            away_team   VARCHAR(50),
            status      VARCHAR(50),
            home_score  INT,
            away_score  INT,
            game_date   DATE,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # New: raw per-game player stats
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            id          SERIAL PRIMARY KEY,
            player_id   INT,
            player_name VARCHAR(100),
            team        VARCHAR(50),
            position    VARCHAR(10),
            game_id     INT,
            game_date   DATE,
            points      FLOAT,
            rebounds    FLOAT,
            assists     FLOAT,
            steals      FLOAT,
            blocks      FLOAT,
            minutes     FLOAT,
            plus_minus  FLOAT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(player_id, game_id)
        );
    """)

    # New: calculated trends per player (upserted every run)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_trends (
            player_id         INT PRIMARY KEY,
            player_name       VARCHAR(100),
            team              VARCHAR(50),
            position          VARCHAR(10),
            season_avg_pts    FLOAT,
            last5_avg_pts     FLOAT,
            season_avg_reb    FLOAT,
            last5_avg_reb     FLOAT,
            season_avg_ast    FLOAT,
            last5_avg_ast     FLOAT,
            trend_direction   VARCHAR(10),  -- 'UP', 'DOWN', 'STABLE'
            trend_magnitude   FLOAT,        -- % above/below season avg
            minutes_avg       FLOAT,
            minutes_last_game FLOAT,
            rest_flag         BOOLEAN,      -- true if minutes dropped >30%
            games_played      INT,
            updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    print("✅ Tables verified/created.")

# ── NBA API helpers ──────────────────────────────────────────────────────────
def fetch_games(api_key, date_str):
    """Fetch all NBA games for a given date."""
    headers = {"Authorization": api_key}
    resp = requests.get(
        f"{NBA_BASE_URL}/games",
        headers=headers,
        params={"dates[]": date_str},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json().get("data", [])

def fetch_player_stats_for_game(api_key, game_id):
    """Fetch all player stats for a specific game."""
    headers = {"Authorization": api_key}
    all_stats = []
    cursor = None

    while True:
        params = {"game_ids[]": game_id, "per_page": 100}
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(
            f"{NBA_BASE_URL}/stats",
            headers=headers,
            params=params,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        all_stats.extend(data.get("data", []))

        # balldontlie uses cursor-based pagination
        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor:
            break

    return all_stats

def parse_minutes(minutes_str):
    """Convert '32:45' format to float minutes."""
    if not minutes_str:
        return 0.0
    try:
        if ":" in str(minutes_str):
            parts = str(minutes_str).split(":")
            return float(parts[0]) + float(parts[1]) / 60
        return float(minutes_str)
    except (ValueError, IndexError):
        return 0.0

# ── Trend calculation ────────────────────────────────────────────────────────
def calculate_trends(cursor):
    """
    For every player with stats in the DB:
    - Calculate season average and last-5-games average for pts/reb/ast
    - Compare to determine UP / DOWN / STABLE trend
    - Flag rest/injury risk if minutes dropped >30% vs average
    Upsert results into player_trends.
    """
    print("📊 Calculating player trends...")

    # Get all unique players who have stats
    cursor.execute("SELECT DISTINCT player_id FROM player_stats;")
    player_ids = [row[0] for row in cursor.fetchall()]
    print(f"   Processing trends for {len(player_ids)} players...")

    trend_rows = []

    for player_id in player_ids:
        # All games for this player (season)
        cursor.execute("""
            SELECT player_name, team, position,
                   points, rebounds, assists,
                   minutes, plus_minus, game_date
            FROM player_stats
            WHERE player_id = %s
            ORDER BY game_date DESC;
        """, (player_id,))
        rows = cursor.fetchall()

        if not rows:
            continue

        player_name = rows[0][0]
        team        = rows[0][1]
        position    = rows[0][2]
        games_played = len(rows)

        # Season averages
        season_avg_pts = sum(r[3] for r in rows) / games_played
        season_avg_reb = sum(r[4] for r in rows) / games_played
        season_avg_ast = sum(r[5] for r in rows) / games_played
        minutes_avg    = sum(r[6] for r in rows) / games_played

        # Last 5 games averages
        last5 = rows[:5]
        last5_avg_pts = sum(r[3] for r in last5) / len(last5)
        last5_avg_reb = sum(r[4] for r in last5) / len(last5)
        last5_avg_ast = sum(r[5] for r in last5) / len(last5)
        minutes_last_game = rows[0][6]  # most recent game

        # Trend direction based on points (primary fantasy metric)
        if season_avg_pts > 0:
            trend_magnitude = ((last5_avg_pts - season_avg_pts) / season_avg_pts) * 100
        else:
            trend_magnitude = 0.0

        if trend_magnitude >= 10:
            trend_direction = "UP"
        elif trend_magnitude <= -10:
            trend_direction = "DOWN"
        else:
            trend_direction = "STABLE"

        # Rest/injury flag: minutes dropped >30% vs average
        rest_flag = (
            minutes_avg > 0 and
            minutes_last_game < minutes_avg * 0.70
        )

        trend_rows.append((
            player_id, player_name, team, position,
            round(season_avg_pts, 1), round(last5_avg_pts, 1),
            round(season_avg_reb, 1), round(last5_avg_reb, 1),
            round(season_avg_ast, 1), round(last5_avg_ast, 1),
            trend_direction, round(trend_magnitude, 1),
            round(minutes_avg, 1), round(minutes_last_game, 1),
            rest_flag, games_played
        ))

    if trend_rows:
        execute_values(cursor, """
            INSERT INTO player_trends (
                player_id, player_name, team, position,
                season_avg_pts, last5_avg_pts,
                season_avg_reb, last5_avg_reb,
                season_avg_ast, last5_avg_ast,
                trend_direction, trend_magnitude,
                minutes_avg, minutes_last_game,
                rest_flag, games_played,
                updated_at
            ) VALUES %s
            ON CONFLICT (player_id) DO UPDATE SET
                player_name       = EXCLUDED.player_name,
                team              = EXCLUDED.team,
                season_avg_pts    = EXCLUDED.season_avg_pts,
                last5_avg_pts     = EXCLUDED.last5_avg_pts,
                season_avg_reb    = EXCLUDED.season_avg_reb,
                last5_avg_reb     = EXCLUDED.last5_avg_reb,
                season_avg_ast    = EXCLUDED.season_avg_ast,
                last5_avg_ast     = EXCLUDED.last5_avg_ast,
                trend_direction   = EXCLUDED.trend_direction,
                trend_magnitude   = EXCLUDED.trend_magnitude,
                minutes_avg       = EXCLUDED.minutes_avg,
                minutes_last_game = EXCLUDED.minutes_last_game,
                rest_flag         = EXCLUDED.rest_flag,
                games_played      = EXCLUDED.games_played,
                updated_at        = CURRENT_TIMESTAMP;
        """, [(
            r[0], r[1], r[2], r[3],
            r[4], r[5], r[6], r[7],
            r[8], r[9], r[10], r[11],
            r[12], r[13], r[14], r[15],
            datetime.utcnow()
        ) for r in trend_rows])

        print(f"✅ Upserted trends for {len(trend_rows)} players.")

# ── Main handler ─────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    print("🚀 SwishOps Lambda triggered at:", datetime.utcnow().isoformat())

    # Fetch secrets
    db_pass_secret = get_secret(DB_PASSWORD_SECRET_ARN)
    db_password    = db_pass_secret.get("password") if isinstance(db_pass_secret, dict) else db_pass_secret

    api_key_secret = get_secret(NBA_API_KEY_SECRET_ARN)
    api_key        = api_key_secret.get("api_key") if isinstance(api_key_secret, dict) else (api_key_secret or "mock-key")

    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    # ── 1. Fetch today's games ───────────────────────────────────────────────
    try:
        games = fetch_games(api_key, today_str)
        print(f"📅 Fetched {len(games)} games for {today_str}.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch games: {e}")
        return {"statusCode": 502, "body": json.dumps(f"NBA API error: {e}")}

    # ── 2. Connect to DB ─────────────────────────────────────────────────────
    conn = None
    try:
        conn = get_db_connection(db_password)
        cursor = conn.cursor()
        create_tables(cursor)

        # ── 3. Store games ───────────────────────────────────────────────────
        games_upserted = 0
        for game in games:
            cursor.execute("""
                INSERT INTO nba_games (
                    game_id, home_team, away_team, status,
                    home_score, away_score, game_date, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (game_id) DO UPDATE SET
                    status     = EXCLUDED.status,
                    home_score = EXCLUDED.home_score,
                    away_score = EXCLUDED.away_score,
                    updated_at = CURRENT_TIMESTAMP;
            """, (
                game.get("id"),
                game.get("home_team", {}).get("name", "Unknown"),
                game.get("visitor_team", {}).get("name", "Unknown"),
                game.get("status", "Scheduled"),
                game.get("home_team_score", 0) or 0,
                game.get("visitor_team_score", 0) or 0,
                today_str
            ))
            games_upserted += 1

        print(f"✅ Upserted {games_upserted} games.")

        # ── 4. Fetch + store player stats for each game ──────────────────────
        total_stats = 0
        for game in games:
            game_id = game.get("id")
            try:
                stats = fetch_player_stats_for_game(api_key, game_id)
            except requests.exceptions.RequestException as e:
                print(f"⚠️  Could not fetch stats for game {game_id}: {e}")
                continue

            for stat in stats:
                player    = stat.get("player", {})
                player_id = player.get("id")
                if not player_id:
                    continue

                cursor.execute("""
                    INSERT INTO player_stats (
                        player_id, player_name, team, position,
                        game_id, game_date,
                        points, rebounds, assists,
                        steals, blocks, minutes, plus_minus
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (player_id, game_id) DO UPDATE SET
                        points     = EXCLUDED.points,
                        rebounds   = EXCLUDED.rebounds,
                        assists    = EXCLUDED.assists,
                        steals     = EXCLUDED.steals,
                        blocks     = EXCLUDED.blocks,
                        minutes    = EXCLUDED.minutes,
                        plus_minus = EXCLUDED.plus_minus;
                """, (
                    player_id,
                    f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
                    stat.get("team", {}).get("name", "Unknown"),
                    player.get("position", ""),
                    game_id,
                    today_str,
                    stat.get("pts", 0) or 0,
                    stat.get("reb", 0) or 0,
                    stat.get("ast", 0) or 0,
                    stat.get("stl", 0) or 0,
                    stat.get("blk", 0) or 0,
                    parse_minutes(stat.get("min", 0)),
                    stat.get("plus_minus", 0) or 0
                ))
                total_stats += 1

        print(f"✅ Upserted {total_stats} player stat records.")

        # ── 5. Calculate and store trends ────────────────────────────────────
        calculate_trends(cursor)

        conn.commit()
        cursor.close()

    except Exception as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
        return {"statusCode": 500, "body": json.dumps(f"Database error: {e}")}
    finally:
        if conn:
            conn.close()

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "SwishOps ingestion complete",
            "date": today_str,
            "games_processed": len(games),
            "player_stats_stored": total_stats
        })
    }
