"""
Proxy for the firewall forwarding logic
This module encapsulates the logic to forward a "clean" inference request
to your actual AI model endpoint and return its response
- Use httpx.AsyncClient to forward the user's JSON payload.
- Set a configurable TARGET_MODEL_URL 
- Raise an error if the model endpoint is unreachable or returns an error.
- Propagate headers 
"""
import httpx
from fastapi import HTTPException
from typing import Dict, Any
import os

TARGET_MODEL_URL = os.getenv("TARGET_MODEL_URL","https://api-inference.huggingface.co/models/gpt2")


async def forward_to_model(
    payload: Dict[str, Any],
    headers: Dict[str, str],
    timeout: float = 30.0
) -> Dict[str, Any]:
    """
    Forward the request to the Hugging Face API.
    Returns the parsed JSON response if successful. Otherwise, raises HTTPException.
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                TARGET_MODEL_URL,
                headers=headers,
                json=payload
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Model endpoint returned error: {response.status_code} {response.text}"
                )
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Error connecting to model endpoint: {e}"
            )
    