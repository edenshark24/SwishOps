import asyncio
import json
import logging
import os
from datetime import date
from typing import Optional

import boto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="SwishOps AI Analytics Service", version="1.0.0")

MODEL_NAME = os.getenv("MODEL_NAME", "nba-stats-predictor-v1")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BACKEND_URL = os.getenv("BACKEND_URL", "http://swishops-backend-svc").rstrip("/")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-opus-5")
BEDROCK_MAX_TOKENS = int(os.getenv("BEDROCK_MAX_TOKENS", "4096"))
BACKEND_TIMEOUT = float(os.getenv("BACKEND_TIMEOUT", "10"))

logging.basicConfig(level=LOG_LEVEL.upper())
logger = logging.getLogger("swishops.ai")

client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

SYSTEM_PROMPT = (
    "You are an NBA fantasy basketball analyst. Base every recommendation strictly "
    "on the stats provided; do not invent numbers. Be concise and actionable."
)


class BedrockError(Exception):
    pass


class RecommendRequest(BaseModel):
    player_id: int
    position: Optional[str] = None


# ── Bedrock ──────────────────────────────────────────────────────────────────
def _invoke_claude_sync(prompt: str) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": BEDROCK_MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        response = client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        payload = json.loads(response["body"].read())
    except (ClientError, BotoCoreError, ValueError) as exc:
        logger.error("Bedrock invocation failed (model=%s): %s", BEDROCK_MODEL_ID, exc)
        raise BedrockError(str(exc)) from exc

    stop_reason = payload.get("stop_reason")
    if stop_reason == "refusal":
        logger.warning("Bedrock refused the request: %s", payload.get("stop_details"))
        raise BedrockError("Model declined the request")
    if stop_reason == "max_tokens":
        logger.warning("Bedrock response truncated at max_tokens=%d", BEDROCK_MAX_TOKENS)

    # Thinking blocks may precede the answer; only return the text blocks.
    text = "".join(
        block.get("text", "")
        for block in payload.get("content", [])
        if block.get("type") == "text"
    ).strip()
    if not text:
        logger.error("Bedrock returned no text content: stop_reason=%s", stop_reason)
        raise BedrockError("Empty response from model")

    usage = payload.get("usage", {})
    logger.info(
        "Bedrock call ok: model=%s input_tokens=%s output_tokens=%s",
        BEDROCK_MODEL_ID, usage.get("input_tokens"), usage.get("output_tokens"),
    )
    return text


async def invoke_claude(prompt: str) -> str:
    # boto3 is blocking; keep it off the event loop.
    return await asyncio.to_thread(_invoke_claude_sync, prompt)


# ── Backend ──────────────────────────────────────────────────────────────────
async def fetch_backend(path: str):
    url = f"{BACKEND_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=BACKEND_TIMEOUT) as http:
            response = await http.get(url)
    except httpx.RequestError as exc:
        logger.error("Backend unreachable at %s: %s", url, exc)
        raise HTTPException(status_code=503, detail="Backend service unavailable")

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Player not found")
    if response.status_code >= 500:
        logger.error("Backend error %d from %s", response.status_code, url)
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    if response.status_code != 200:
        logger.error("Unexpected backend status %d from %s", response.status_code, url)
        raise HTTPException(status_code=502, detail="Unexpected backend response")
    return response.json()


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": MODEL_NAME}

@app.post("/api/ai/predict")
async def predict_trends(data: dict):
    return {
        "model_used": MODEL_NAME,
        "prediction": "High likelihood of high-scoring fourth quarter based on historical pace."
    }


@app.post("/api/ai/recommend")
async def recommend(req: RecommendRequest):
    data = await fetch_backend(f"/api/players/{req.player_id}")
    trend = data.get("player") or {}
    player_name = trend.get("player_name", f"Player {req.player_id}")
    position = req.position or trend.get("position") or "unknown"

    prompt = (
        f"Give a fantasy basketball recommendation for {player_name} "
        f"(position: {position}).\n\n"
        f"Season trend data:\n{json.dumps(trend, indent=2, default=str)}\n\n"
        f"Most recent games:\n"
        f"{json.dumps(data.get('recent_games', []), indent=2, default=str)}\n\n"
        "Answer with: a verdict (START, SIT, or WATCH), a 2-3 sentence rationale "
        "citing the stats, and the key risk to monitor."
    )

    logger.info("Requesting recommendation for player_id=%d", req.player_id)
    try:
        recommendation = await invoke_claude(prompt)
    except BedrockError:
        raise HTTPException(status_code=502, detail="AI model request failed")

    return {"player": player_name, "recommendation": recommendation, "stats_used": trend}


@app.post("/api/ai/weekly-picks")
async def weekly_picks():
    risers = await fetch_backend("/api/trends/risers")
    risers = risers[:10]
    if not risers:
        return {"week": date.today().isoformat(), "picks": "No trending players available.", "players_analyzed": 0}

    prompt = (
        "Here are this week's top trending NBA players by trend magnitude:\n\n"
        f"{json.dumps(risers, indent=2, default=str)}\n\n"
        "Rank them as weekly fantasy picks from best to worst. For each, give one "
        "line: rank, player name, and the stat-based reason. Flag any rest or "
        "minutes-related risk."
    )

    logger.info("Requesting weekly picks for %d players", len(risers))
    try:
        picks = await invoke_claude(prompt)
    except BedrockError:
        raise HTTPException(status_code=502, detail="AI model request failed")

    return {"week": date.today().isoformat(), "picks": picks, "players_analyzed": len(risers)}
