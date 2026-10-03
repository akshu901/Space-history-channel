import json, os, time, logging, requests
from config import settings

log = logging.getLogger("llm")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"

# Google retires models often. We try these in order and skip any that return 404.
# Set GEMINI_MODEL to force one model first.
FALLBACK_MODELS = [
    "gemini-3-flash-preview",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash",
]

def _models():
    first = os.getenv("GEMINI_MODEL")
    return ([first] if first else []) + [m for m in FALLBACK_MODELS if m != first]

def _unwrap(obj):
    """Some models wrap the JSON object in a one-item list: [ {...} ]. Unwrap it."""
    while isinstance(obj, list) and len(obj) == 1:
        obj = obj[0]
    return obj

def generate_json(prompt: str, retries: int = 4):
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7}}
    errors = []
    for model in _models():
        for i in range(retries):
            try:
                r = requests.post(URL.format(m=model), json=body, timeout=180,
                                  headers={"x-goog-api-key": settings.GEMINI_API_KEY})
                if r.status_code == 404:
                    errors.append(f"{model}: 404 not available")
                    break  # try next model
                if r.status_code in (429, 500, 503):
                    time.sleep(2 ** (i + 2)); continue
                r.raise_for_status()
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                log.info("Used model %s", model)
                return _unwrap(json.loads(text))
            except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
                if i == retries - 1:
                    errors.append(f"{model}: {e}")
                time.sleep(2 ** (i + 1))
    raise RuntimeError("All Gemini models failed: " + " | ".join(errors))
