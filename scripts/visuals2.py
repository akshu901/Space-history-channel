"""Phase 3b (v2): timeline.json -> NASA images per section -> images/, visuals.json, credits.txt"""
import json, logging, re, shutil, sys, time, urllib.parse, urllib.request
from config import settings
from scripts.llm import generate_json

log = logging.getLogger("visuals")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

UA = {"User-Agent": "space-history-channel/1.0"}
SECONDS_PER_IMAGE = 8
MAX_PER_SECTION = 8
MIN_BORROW = 3


def latest_dir():
    dirs = [d for d in settings.OUTPUT_DIR.iterdir() if (d / "timeline.json").exists()]
    if not dirs:
        raise RuntimeError("No timeline.json found. Run voiceover first.")
    return max(dirs, key=lambda d: d.stat().st_mtime)


def http_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def download(url, path):
    safe = urllib.parse.quote(url, safe=":/%?&=~")
    req = urllib.request.Request(safe, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if len(data) < 20_000:
        raise RuntimeError("image too small")
    path.write_bytes(data)


def make_queries(title, sections):
    lines = "\n".join(f"{s['name']}: {s['visual_hint']}" for s in sections)
    prompt = (
        f"Video title: {title}\n"
        "For each section below, give 3 short search queries (2 to 4 words each) for the NASA Image "
        "and Video Library that would find real photos matching the section. Use specific names "
        "(spacecraft parts, people, places).\n"
        'Also add a key "general" with 5 broad queries about the whole video topic '
        "(crew, mission, spacecraft).\n"
        'Return JSON only: {"queries": {"hook": ["...", "...", "..."], "general": ["...", "..."]}}\n'
        f"SECTIONS:\n{lines}"
    )
    try:
        return generate_json(prompt)["queries"]
    except Exception:
        log.warning("Query generation failed, using fallback queries")
        return {}


def search(q):
    url = ("https://images-api.nasa.gov/search?q=" + urllib.parse.quote(q)
           + "&media_type=image&page_size=30")
    try:
        items = http_json(url)["collection"]["items"]
        log.info("search %r -> %d results", q, len(items))
        return items
    except Exception as e:
        log.warning("Search failed for %r: %s", q, e)
        return []


def best_asset(item):
    urls = http_json(item["href"])
    jpgs = [u for u in urls if u.lower().endswith(".jpg")]
    for tag in ("~large.jpg", "~medium.jpg"):
        for u in jpgs:
            if u.lower().endswith(tag):
                return u
    links = item.get("links") or []
    if links:
        return links[0]["href"]
    raise RuntimeError("no usable image file")


def run():
    out = latest_dir()
    log.info("Using %s", out)
    script = json.loads((out / "script.json").read_text())
    sections = json.loads((out / "timeline.json").read_text())["sections"]
    title = script["title"]
    queries = make_queries(title, sections)
    general = queries.get("general") or [re.sub(r"[^\w ]", "", title.split(":")[-1]).strip(), "Apollo 13"]

    img_dir = out / "images"
    img_dir.mkdir(exist_ok=True)
    used, result = set(), []

    for sec in sections:
        need = max(1, min(MAX_PER_SECTION, round(sec["duration"] / SECONDS_PER_IMAGE)))
        got = []
        for q in (queries.get(sec["name"]) or []) + general:
            if len(got) >= need:
                break
            for item in search(q):
                if len(got) >= need:
                    break
                d = item["data"][0]
                nid = d["nasa_id"]
                if nid in used:
                    continue
                path = img_dir / f"{sec['name']}_{len(got) + 1:02d}.jpg"
                try:
                    download(best_asset(item), path)
                except Exception as e:
                    log.warning("Skip %s: %s", nid, e)
                    continue
                used.add(nid)
                got.append({"file": f"images/{path.name}", "nasa_id": nid,
                            "title": d.get("title", ""), "center": d.get("center", ""),
                            "source_url": f"https://images.nasa.gov/details/{nid}"})
                time.sleep(0.3)
        log.info("%s: %d/%d images", sec["name"], len(got), need)
        result.append({"name": sec["name"], "duration": sec["duration"], "images": got, "need": need})

    if not used:
        raise RuntimeError("No images found for any section")

    # sections that still have too few images borrow from the section with the most
    donor = max(result, key=lambda s: len(s["images"]))
    for sec in result:
        want = min(MIN_BORROW, sec["need"])
        if len(sec["images"]) >= want:
            continue
        for k, im in enumerate(donor["images"]):
            if len(sec["images"]) >= want:
                break
            dst = img_dir / f"{sec['name']}_borrowed_{k + 1:02d}.jpg"
            shutil.copy(out / im["file"], dst)
            sec["images"].append({**im, "file": f"images/{dst.name}", "borrowed_from": donor["name"]})
        log.warning("%s borrowed images from %s", sec["name"], donor["name"])

    (out / "visuals.json").write_text(json.dumps(result, indent=2))
    credits = ["Images: NASA Image and Video Library (images.nasa.gov)"]
    seen = set()
    for sec in result:
        for im in sec["images"]:
            if im["nasa_id"] in seen:
                continue
            seen.add(im["nasa_id"])
            credits.append(f"- {im['title']} | NASA {im['center']} | {im['source_url']}")
    (out / "credits.txt").write_text("\n".join(credits))
    log.info("Done. %d unique images", len(used))


if __name__ == "__main__":
    try:
        run()
    except Exception:
        log.exception("Visuals step failed")
        sys.exit(1)
