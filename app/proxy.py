"""
Proxy for the firewall forwarding logic
This module encapsulates the logic to forward a "clean" inference request
to your actual AI model endpoint and return its response
- Use httpx.AsyncClient to forward the user's JSON payload.
- Set a configurable TARGET_MODEL_URL 
- Raise an error if the model endpoint is unreachable or returns an error.
- Propagate headers 
"""
from typing import Dict, Any
import os
import httpx
from fastapi import HTTPException

TARGET_MODEL_URL = os.getenv("TARGET_MODEL_URL",
                            "https://router.huggingface.co/fireworks-ai/inference/v1/chat/completions")


async def forward_to_model(
    payload: Dict[str, Any],
    headers: Dict[str, str],
    timeout: float = 30.0
) -> Dict[str, Any]:
    """
    Forward the request to the Hugging Face API.
    Returns the parsed JSON response if successful. Otherwise, raises HTTPException.
    """
    # Clean headers - remove problematic ones that httpx should handle automatically
    clean_headers = {}
    headers_to_skip = {
        'content-length', 'content-encoding', 'transfer-encoding', 
        'connection', 'host', 'accept-encoding'
    }

    for key, value in headers.items():
        if key.lower() not in headers_to_skip:
            clean_headers[key] = value

    # Ensure we have the required authorization header for HuggingFace
    hf_api_key = os.getenv("HF_API_KEY")
    if hf_api_key:
        clean_headers["Authorization"] = f"Bearer {hf_api_key}"
    
    # Ensure content-type is set for JSON
    clean_headers["Content-Type"] = "application/json"

    modified_payload = payload.copy()
    if "model" not in modified_payload:
        modified_payload["model"] = "accounts/fireworks/models/deepseek-r1-0528"

    # Transform simple inputs format to chat completions format if needed
    if "inputs" in modified_payload and "messages" not in modified_payload:
        user_input = modified_payload.pop("inputs")
        modified_payload["messages"] = [
            {"role": "user", "content": user_input}
        ]

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            # Forward the request to the target model URL
            response = await client.post(
                TARGET_MODEL_URL,
                headers=clean_headers,
                json=modified_payload
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
    