import json, time, requests
from config import settings

URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"

def generate_json(prompt: str, retries: int = 4):
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7}}
    for i in range(retries):
        try:
            r = requests.post(URL.format(m=settings.GEMINI_MODEL), json=body, timeout=120,
                              headers={"x-goog-api-key": settings.GEMINI_API_KEY})
            if r.status_code in (429, 500, 503):
                time.sleep(2 ** (i + 2)); continue
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
            if i == retries - 1:
                raise RuntimeError(f"LLM call failed: {e}")
            time.sleep(2 ** (i + 1))
    raise RuntimeError("LLM call failed after retries (rate limited?)")
