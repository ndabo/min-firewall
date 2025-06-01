"""
FastAPI application for managing firewall rules.
"""
from typing import Dict, List
import os
import time
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.filters import is_blocked
from app.proxy import forward_to_model
import app.proxy as proxy_module
from app.logger import get_logger
from dotenv import load_dotenv

load_dotenv()


app = FastAPI(title = "Model Inference Firewall (MIF)")

logger = get_logger("mif_firewall")
# # configuration
# HF_API_KEY = os.getenv("HF_API_KEY")
# MODEL = "gpt2"
# HEADERS = {
#     "Authorization": f"Bearer {HF_API_KEY}",
#     "Content-Type": "application/json"
# }

# HF_API_URL = os.getenv("TARGET_MODEL_URL",
#                         "https://router.huggingface.co/fireworks-ai/inference/v1/chat/completions")


# ------------------------
# 1) Simple in-memory rate limiter
# ------------------------
# For demo purposes only. 
# A production system should use Redis or an external store so that concurrency/multi‐process works properly.

RATE_LIMIT = 10        # maximum number of calls
RATE_WINDOW = 60       # per window in seconds (e.g. 10 requests per 60 seconds)

# Store: { client_ip: [timestamp1, timestamp2, ...] }
request_timestamps: Dict[str, List[float]] = {}

def is_rate_limited(client_ip: str) -> bool:
    """
    Return True if `client_ip` has exceeded RATE_LIMIT in the last RATE_WINDOW seconds.
    """
    now = time.time()
    if client_ip not in request_timestamps: #check if the client has made any request
        request_timestamps[client_ip] = [now]
        return False
    window_start = now - RATE_WINDOW
    timestamps = [ts for ts in request_timestamps[client_ip] if ts >=window_start]
    timestamps.append(now)
    request_timestamps[client_ip] = timestamps

    return len(timestamps) > RATE_LIMIT




@app.post("/infer")
async def proxy_to_hf(request: Request):
    """
    Proxy the request to the OpenAI API.
    - Parse JSON payload
    - Rate‐limit by client IP
    - Filter prompt
    - Log request
    - Forward to model
    - Return response (or blocked/rate‐limited error)
    """
    client_ip = request.client.host or "unknown"
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Request must be valid json" 
        )
    prompt = body.get("prompt") or body.get("messages") or body.get("inputs") or None
    #Normalize: if the user uses `messages` (chat format), stringify for filtering
    if isinstance(prompt,list):
        prompt_txt = " ".join(item.get("content","") for item in prompt)
    elif isinstance(prompt,str):
        prompt_txt = prompt
    else: 
        prompt_txt = ""
    
    # --- Rate limiting ---
    if is_rate_limited(client_ip):
        logger.warning(f"Rate limit exceeded for IP {client_ip}.")
        raise HTTPException(
            status_code = status.HTTP_429_TOO_MANY_REQUESTS,
            detail = "Rate limit exceeded. Please try again later."
        )

     # --- Prompt filtering ---
    blocked, reason = is_blocked(prompt_txt)
    if blocked:
        logger.warning(f"Blocked request from IP {client_ip}: {reason} -- Prompt: {prompt_txt!r}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Prompt blocked by MIF", "reason": reason}
        )
    
    # --- Log the allowed request at INFO ---
    logger.info(f"Allowed request from IP {client_ip}: prompt_preview={prompt_txt[:50]!r}")

    # --- Forward to actual model endpoint ---
    try:
        model_response = await proxy_module.forward_to_model(body, dict(request.headers))
    except HTTPException as e:
        # Already logged/constructed by forward_to_model
        raise e

    # --- Return the model’s JSON straight back to the client ---
    return JSONResponse(content=model_response, status_code=200)


    