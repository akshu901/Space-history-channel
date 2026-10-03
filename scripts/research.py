"""Free research: Wikipedia (CC BY-SA) + NASA Image and Video Library (mostly public domain)."""
import requests
from config.settings import USER_AGENT

HEADERS = {"User-Agent": USER_AGENT}

def wikipedia(query: str, max_chars: int = 9000):
    r = requests.get("https://en.wikipedia.org/w/api.php", headers=HEADERS, timeout=30, params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": query,
        "gsrlimit": 2, "prop": "extracts|info", "explaintext": 1, "exlimit": 2, "inprop": "url"})
    r.raise_for_status()
    pages = (r.json().get("query") or {}).get("pages", {})
    out = []
    for p in sorted(pages.values(), key=lambda x: x.get("index", 99)):
        out.append({"title": p["title"], "url": p["fullurl"], "license": "CC BY-SA 4.0 (Wikipedia)",
                    "text": (p.get("extract") or "")[:max_chars]})
    return out

def nasa_images(query: str, limit: int = 8):
    """Candidate images for Phase 3. NASA media is generally not copyrighted,
    but each item must be checked for credit/'copyright' fields before use."""
    r = requests.get("https://images-api.nasa.gov/search", headers=HEADERS, timeout=30,
                     params={"q": query, "media_type": "image"})
    r.raise_for_status()
    items = r.json()["collection"]["items"][:limit]
    res = []
    for it in items:
        d = it["data"][0]
        res.append({"nasa_id": d["nasa_id"], "title": d.get("title"), "center": d.get("center"),
                    "date": d.get("date_created"), "preview": it["links"][0]["href"] if it.get("links") else None,
                    "page": f"https://images.nasa.gov/details/{d['nasa_id']}",
                    "license": "NASA media usage guidelines (generally public domain)"})
    return res

def gather(query: str):
    return {"sources": wikipedia(query), "images": nasa_images(query)}
