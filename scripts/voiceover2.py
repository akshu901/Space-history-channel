"""Phase 3a: script.json -> per-section mp3 -> voice.mp3 + timeline.json"""
import asyncio, json, subprocess, logging
import edge_tts
from config import settings

log = logging.getLogger("voiceover")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

VOICE = "en-US-GuyNeural"   # other options: en-US-AriaNeural, en-GB-RyanNeural
RATE = "-5%"                # slightly slower = clearer for history content


def latest_dir():
    dirs = [d for d in settings.OUTPUT_DIR.iterdir() if (d / "script.json").exists()]
    if not dirs:
        raise RuntimeError("No script.json found in output/")
    return max(dirs, key=lambda d: d.stat().st_mtime)


def duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True)
    return round(float(r.stdout.strip()), 2)


async def synth(text, path):
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(path))


def run():
    out = latest_dir()
    log.info("Using %s", out)
    script = json.loads((out / "script.json").read_text())
    audio = out / "audio"
    audio.mkdir(exist_ok=True)

    timeline, files, start = [], [], 0.0
    for i, sec in enumerate(script["sections"]):
        mp3 = audio / f"{i:02d}_{sec['name']}.mp3"
        asyncio.run(synth(sec["narration"], mp3))
        d = duration(mp3)
        timeline.append({"name": sec["name"], "file": mp3.name, "start": round(start, 2),
                         "duration": d, "visual_hint": sec["visual_hint"]})
        files.append(mp3)
        start += d
        log.info("%s: %.1fs", sec["name"], d)

    listfile = audio / "list.txt"
    listfile.write_text("".join(f"file '{f.resolve()}'\n" for f in files))
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
                    "-c", "copy", str(out / "voice.mp3")], check=True, capture_output=True)

    (out / "timeline.json").write_text(json.dumps(
        {"total_seconds": round(start, 2), "sections": timeline}, indent=2))
    log.info("Done. Total %.1fs -> %s", start, out / "voice.mp3")


if __name__ == "__main__":
    run()
