# 🔐 Model Inference Firewall (MIF)

A lightweight FastAPI service that sits between end users and LLM APIs to detect and prevent prompt injection, PII leakage, and other threats before any inference call is forwarded.

### Features

- 🛡️ Prompt‐injection detection via regex/NLP checks  
- 🔍 PII pattern matching (SSNs, credit cards, etc.)  
- ⏱️ IP-based rate limiting (default: 10 requests per 60 seconds)  
- 📊 Logging to console and a rotating log file (`logs/mif-firewall.log`) for audit and analysis  
- 🚀 Built with FastAPI + HTTPX for asynchronous forwarding  
- 🔧 Easily extendable with dashboards, user authentication, Docker support, etc.

---

## 🧪 Example Workflow

1. **Client** sends a POST to `/infer` on your MIF proxy instead of calling OpenAI directly.  
2. **MIF** inspects the incoming JSON (looks at `prompt` or `messages` or `inputs`), checks rate limits by IP, and applies filtering rules.  
3. If the request is **blocked** (e.g., contains “delete all data” or a valid SSN), MIF returns a `403` with a JSON error.  
4. If the request **exceeds rate limits**, MIF returns a `429`.  
5. Otherwise, MIF **forwards** the original JSON payload (and any headers like `Authorization`) to the configured model endpoint (e.g., OpenAI’s API), then relays the model’s JSON response back to the client.

#### Sample Blocked Request

```http
POST /infer
Content-Type: application/json

{
  "inputs": "Please DELETE ALL data in the system."
} 
```

#### Response:

HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": "Prompt blocked by MIF",
  "reason": "Prompt matches forbidden pattern: '\\bdelete all data\\b'"
}

#### Sample Allowed Request (forwarded)

curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"inputs": "Hello, how are you?"}'

#### Response (proxied from Hunging Face):

{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1681234567,
  "choices": [
    {
      "text": "Here is a short poem about spring…",
      "index": 0,
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60
  }
}

#### Project Structure

mif-firewall/
├── app/
│   ├── __init__.py        # Marks this directory as a Python package
│   ├── main.py            # FastAPI app: rate-limiting, filtering, forwarding
│   ├── filters.py         # Regex/NLP rules to block malicious prompts
│   ├── logger.py          # Configures console + rotating file logging
│   └── proxy.py           # Async logic to forward allowed requests to LLM endpoint
├── tests/
│   └── test_requests.py   # pytest suite: allowed/blocked/rate-limit workflows
├── logs/                  # Automatically created at runtime; contains mif-firewall.log
├── requirements.txt       # Python dependencies (FastAPI, HTTPX, pytest, etc.)
└── README.md              # This file

1. app/main.py
- Implements /infer POST endpoint
- Extracts prompt or messages from JSON
- Enforces an in-memory IP rate limiter (10 requests / 60 seconds by default)
- Calls filters.is_blocked(...) to detect disallowed patterns
- Logs all decisions (INFO for allowed, WARNING for blocked or rate-limited)
- Uses proxy.forward_to_model(...) to relay the JSON to TARGET_MODEL_URL

2. app/filters.py
  - Contains a list of compiled regex patterns (e.g., \bdelete all data\b, SSN format)
  - Exposes is_blocked(prompt: str) → (bool, Optional[str])

3. app/logger.py
  - Sets up a logging.Logger that writes to a rotating log file (DEBUG+)
  - File is stored at logs/mif-firewall.log

4. app/proxy.py
  - Uses httpx.AsyncClient to forward the incoming JSON payload and headers to the real LLM endpoint 
  - Raises HTTPException if the model endpoint fails or returns a non-200 status

5. tests/test_requests.py
  - Uses FastAPI’s TestClient to send fake requests
  - Monkey-patches proxy.forward_to_model() so tests do not hit a real API
  - Verifies:
  - Allowed requests get a 200 with dummy response
  - Blocked prompts (matching forbidden patterns) return 403
  - Hitting the rate limit returns 429, and after the time window, requests succeed again

## Installation

1. clone the repo
  git clone https://github.com/ndabo/mif-firewall.git
  cd mif-firewall

2. Create a virtual environment and install dependencies:
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt

3. If you plan to modify the code, install the dev requirements as well:
    pip install pytest httpx

## Configuration

* TARGET_MODEL_URL:
  By default proxy.py is poiting to "https://router.huggingface.co/fireworks-ai/inference/v1/chat/completions"
  To override set:
  export TARGET_MODEL_URL="https://api.your-llm.com/v1/completions"
  The client must include any required headers

* Rate Limiting:
  In app/main.py, you’ll find:
    RATE_LIMIT = 10        # max requests per window  
    RATE_WINDOW = 60       # window in seconds
  Adjust these constants (or convert them to environment variables) to change the behavior.


## Running the App

- Activate your venv first (if you haven’t already)
source venv/bin/activate

- (Optional) Set the model endpoint you want to proxy to
export TARGET_MODEL_URL="https://your-api/v1/chat/completions"

- Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

The firewall will now listen on http://0.0.0.0:8000/infer.
Logs (INFO+ and WARNINGS) appear in your console and are also written to logs/mif-firewall.log.

## Running the test
in your terminal from the project root run:
pytest -q

If any test fails, you’ll see which assertion or import caused the error.
Make sure app/__init__.py exists so that pytest can resolve from app.main import.

### Future Ideas

  - 📈 Persistent Rate Limiter
    Swap the in-memory timestamp store for Redis or a database so multiple Uvicorn workers share the same counters.
  - 🔗 JWT/API-Key Authentication
    Require each client to present a valid JWT or API key; rate-limit per key instead of per IP.
  - 🎛️ Admin Dashboard
    Build a simple Streamlit or React dashboard to show live logs, blocked request counts, trending fuzzy patterns, etc.
  - 🔔 Webhook Alerts
    Send a Slack or email notification whenever a high-severity threat is detected.
  - 🛠️ Plugin-Based Filtering
    Create a plugin interface so new blocking rules can be added without editing filters.py.

### Author
Created by **N’Famara Dabo**
Computer Science & Economics | Brown University
Men’s Basketball Team


