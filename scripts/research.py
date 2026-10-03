"""Free research: Wikipedia (CC BY-SA) + NASA Image and Video Library (mostly public domain)."""
import requests
from urllib.parse import quote
from config.settings import USER_AGENT

HEADERS = {"User-Agent": USER_AGENT}

def wikipedia(query: str, max_chars: int = 60000, pages: int = 2):
    """Find the top matching articles, then fetch each FULL article text separately."""
    api = "https://en.wikipedia.org/w/api.php"
    s = requests.get(api, headers=HEADERS, timeout=30, params={
        "action": "query", "format": "json", "list": "search",
        "srsearch": query, "srlimit": pages})
    s.raise_for_status()
    out = []
    for hit in s.json()["query"]["search"]:
        title = hit["title"]
        r = requests.get(api, headers=HEADERS, timeout=30, params={
            "action": "query", "format": "json", "prop": "extracts",
            "explaintext": 1, "titles": title, "redirects": 1})
        r.raise_for_status()
        page = next(iter(r.json()["query"]["pages"].values()))
        text = page.get("extract") or ""
        if len(text) < 500:
            continue
        out.append({"title": title,
                    "url": "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_")),
                    "license": "CC BY-SA 4.0 (Wikipedia)",
                    "text": text[:max_chars]})
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
