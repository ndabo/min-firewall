"""
FastAPI application for managing firewall rules.
"""

from fastapi import FastAPI
import requests
from dotenv import load_dotenv
import os
from filters import is_prompt_injection, contains_pii
from logger import log_request

load_dotenv()


app = FastAPI()

# configuration
HF_API_KEY = os.getenv("HF_API_KEY")
MODEL = "gpt2"
HEADERS = {
    "Authorization": f"Bearer {HF_API_KEY}",
    "Content-Type": "application/json"
}

HF_API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"

@app.post("/proxy")
async def proxy_to_hf(request: Request):
    """
    Proxy the request to the OpenAI API.
    """
    body = await request.json()
    prompt = body.get("prompt", "")
    







# if __name__ == "__main__":