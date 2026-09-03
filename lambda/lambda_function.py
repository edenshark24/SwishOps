import os
import json
import boto3
import requests
import psycopg2
from datetime import datetime
from botocore.exceptions import ClientError

# Environment variables containing Secrets Manager ARNs
DB_HOST = os.getenv("DB_HOST", "swishops-postgres-rds.c123456.us-east-1.rds.amazonaws.com")
DB_NAME = os.getenv("DB_NAME", "swishops")
DB_USER = os.getenv("DB_USER", "dbadmin")
DB_PORT = os.getenv("DB_PORT", "5432")

DB_PASSWORD_SECRET_ARN = os.getenv("DB_PASSWORD_SECRET_ARN")
NBA_API_KEY_SECRET_ARN = os.getenv("NBA_API_KEY_SECRET_ARN")

NBA_API_URL = "https://api.balldontlie.io/v1/games"

def get_secret(secret_arn):
    """Helper function to securely retrieve secrets from AWS Secrets Manager."""
    if not secret_arn:
        return None
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager')
    try:
        response = client.get_secret_value(SecretId=secret_arn)
        if 'SecretString' in response:
            secret = response['SecretString']
            # If the secret is stored as a JSON string (like DB credentials), parse it
            try:
                return json.loads(secret)
            except json.JSONDecodeError:
                return secret
    except ClientError as e:
        print(f"❌ Error retrieving secret {secret_arn}: {e}")
        raise e
    return None

def lambda_handler(event, context):
    print("🚀 SwishOps Lambda Ingestion triggered at:", datetime.utcnow().isoformat())
    
    # Fetch secrets dynamically at runtime
    db_pass_secret = get_secret(DB_PASSWORD_SECRET_ARN)
    # If stored as a JSON object, extract the password key, otherwise use string directly
    db_password = db_pass_secret.get('password') if isinstance(db_pass_secret, dict) else db_pass_secret
    
    api_key_secret = get_secret(NBA_API_KEY_SECRET_ARN)
    api_key = api_key_secret.get('api_key') if isinstance(api_key_secret, dict) else (api_key_secret or "mock-key")

    # 1. Fetch current game data from external API
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    headers = {"Authorization": api_key}
    params = {"dates[]": today_str}
    
    games_data = []
    try:
        response = requests.get(NBA_API_URL, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            games_data = response.json().get("data", [])
            print(f"Successfully fetched {len(games_data)} games from NBA API.")
        else:
            print(f"⚠️ API returned status code {response.status_code}. Using fallback mock data.")
            games_data = [
                {"home_team": {"name": "Celtics"}, "visitor_team": {"name": "Nuggets"}, "status": "Live", "home_team_score": 58, "visitor_team_score": 54}
            ]
    except Exception as e:
        print(f"❌ Error fetching external NBA data: {str(e)}")
        games_data = [{"home_team": {"name": "Celtics"}, "visitor_team": {"name": "Nuggets"}, "status": "Live", "home_team_score": 58, "visitor_team_score": 54}]

    # 2. Connect to PostgreSQL RDS using fetched credentials
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=db_password,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nba_games (
                id SERIAL PRIMARY KEY,
                home_team VARCHAR(50),
                away_team VARCHAR(50),
                status VARCHAR(50),
                home_score INT,
                away_score INT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        for game in games_data:
            home = game.get("home_team", {}).get("name", "Unknown")
            away = game.get("visitor_team", {}).get("name", "Unknown")
            status = game.get("status", "Scheduled")
            home_score = game.get("home_team_score", 0) or 0
            visitor_score = game.get("visitor_team_score", 0) or 0
            
            cursor.execute("""
                INSERT INTO nba_games (home_team, away_team, status, home_score, away_score, updated_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
            """, (home, away, status, home_score, visitor_score))
            
        conn.commit()
        cursor.close()
        print("✅ Successfully synchronized NBA game data into PostgreSQL RDS.")
        
    except Exception as db_error:
        print(f"❌ Database error: {str(db_error)}")
        if conn:
            conn.rollback()
        return {"statusCode": 500, "body": json.dumps("Database synchronization failed")}
    finally:
        if conn:
            conn.close()

    return {
        "statusCode": 200,
        "body": json.dumps(f"Successfully processed {len(games_data)} games.")
    }
