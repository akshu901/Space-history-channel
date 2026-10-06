"""Phase 3c: images + voice.mp3 + script -> captions.srt + video.mp4 (720p, slow zoom, burned-in subtitles)"""
import json, logging, re, subprocess, sys
from config import settings

log = logging.getLogger("render")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

W, H, FPS = 1280, 720, 24
ZOOM = 0.15          # total zoom amount per image
MAX_WORDS_PER_CAPTION = 8


def latest_dir():
    dirs = [d for d in settings.OUTPUT_DIR.iterdir()
            if (d / "visuals.json").exists() and (d / "voice.mp3").exists()]
    if not dirs:
        raise RuntimeError("No folder with visuals.json and voice.mp3. Run voiceover and visuals first.")
    return max(dirs, key=lambda d: d.stat().st_mtime)


def sh(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd[:6])} ...\n{r.stderr[-1500:]}")
    return r


def image_ok(out, rel):
    # really decode one frame; corrupt or non-image files fail here
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", rel, "-frames:v", "1", "-f", "null", "-"],
                       cwd=out, capture_output=True, text=True)
    return r.returncode == 0 and not r.stderr.strip()


# ---------- subtitles ----------
def clean_for_display(text):
    # "N-A-S-A" -> "NASA", "P-M" -> "PM" (the script spells these out for the voice)
    return re.sub(r"\b(?:[A-Z]-)+[A-Z]\b", lambda m: m.group(0).replace("-", ""), text)


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def chunk_words(words, n):
    parts = max(1, -(-len(words) // n))          # ceil division
    size = -(-len(words) // parts)
    return [words[i:i + size] for i in range(0, len(words), size)]


def build_srt(timeline_sections, script):
    narr = {s["name"]: s["narration"] for s in script["sections"]}
    entries = []
    for sec in timeline_sections:
        text = clean_for_display(narr.get(sec["name"], ""))
        sentences = [x for x in re.split(r"(?<=[.!?\"\u201d])\s+(?=[A-Z\"\u201c])", text.strip()) if x]
        pieces = []
        for sent in sentences:
            pieces += [" ".join(c) for c in chunk_words(sent.split(), MAX_WORDS_PER_CAPTION)]
        total = sum(len(p.split()) for p in pieces) or 1
        t = sec["start"]
        for p in pieces:
            dur = sec["duration"] * len(p.split()) / total
            words = p.split()
            if len(words) > 5:
                mid = len(words) // 2
                p = " ".join(words[:mid]) + "\n" + " ".join(words[mid:])
            entries.append((t, t + dur, p))
            t += dur
    lines = []
    for i, (a, b, p) in enumerate(entries, 1):
        lines += [str(i), f"{srt_time(a)} --> {srt_time(b)}", p, ""]
    return "\n".join(lines)


# ---------- video ----------
def make_clip(out, img, frames, zoom_in, dst):
    n = max(frames, 1)
    z = f"1+{ZOOM}*on/{n}" if zoom_in else f"{1 + ZOOM}-{ZOOM}*on/{n}"
    vf = (f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
          f"zoompan=z={z}:x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):d={n}:s={W}x{H}:fps={FPS},"
          f"format=yuv420p")
    sh(["ffmpeg", "-y", "-i", img, "-vf", vf, "-frames:v", str(n),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-r", str(FPS), dst], out)


def run():
    out = latest_dir()
    log.info("Using %s", out)
    script = json.loads((out / "script.json").read_text())
    timeline = json.loads((out / "timeline.json").read_text())["sections"]
    visuals = json.loads((out / "visuals.json").read_text())

    (out / "clips").mkdir(exist_ok=True)
    clips, idx, elapsed_frames = [], 0, 0
    for sec, vis in zip(timeline, visuals):
        imgs = [im["file"] for im in vis["images"] if image_ok(out, im["file"])]
        if not imgs:
            raise RuntimeError(f"Section {sec['name']} has no usable images")
        sec_start, sec_end = sec["start"], sec["start"] + sec["duration"]
        per = (sec_end - sec_start) / len(imgs)
        for k, img in enumerate(imgs):
            end_f = round((sec_start + per * (k + 1)) * FPS)
            start_f = round((sec_start + per * k) * FPS)
            frames = max(end_f - start_f, 1)
            dst = f"clips/c{idx:03d}.mp4"
            make_clip(out, img, frames, zoom_in=(idx % 2 == 0), dst=dst)
            clips.append(dst)
            idx += 1
        log.info("%s: %d clips", sec["name"], len(imgs))

    (out / "clips.txt").write_text("".join(f"file '{c}'\n" for c in clips))
    srt = build_srt(timeline, script)
    (out / "captions.srt").write_text(srt)

    style = ("FontName=DejaVu Sans,FontSize=16,Bold=1,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H00000000,Outline=2,Shadow=0,Alignment=2,MarginV=28")
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "clips.txt", "-i", "voice.mp3",
        "-vf", f"subtitles=captions.srt:force_style='{style}'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", "video.mp4"], out)

    for c in clips:
        (out / c).unlink()
    (out / "clips").rmdir()
    (out / "clips.txt").unlink()
    size = (out / "video.mp4").stat().st_size / 1_000_000
    log.info("Done. video.mp4 is %.1f MB with %d clips", size, len(clips))


if __name__ == "__main__":
    try:
        run()
    except Exception:
        log.exception("Render step failed")
        sys.exit(1)
