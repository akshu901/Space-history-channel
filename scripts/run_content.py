"""Phase 2 runner: topic -> research -> script -> fact-check -> saved to output/ and DB."""
import json, logging, sys
from datetime import date
from config import settings
from scripts import db, topics, research
from scripts.script_writer import write_script, word_count
from scripts.fact_check import fact_check

settings.LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.FileHandler(settings.LOG_DIR / "pipeline.log"), logging.StreamHandler()])
log = logging.getLogger("content")

def run():
    conn = db.connect()
    t = topics.pick_topic(conn)
    vid = db.reserve_topic(conn, t["topic"])
    out = settings.OUTPUT_DIR / f"{date.today()}_{db.slugify(t['topic'])}"
    out.mkdir(parents=True, exist_ok=True)
    try:
        log.info("Topic: %s", t["topic"])
        data = research.gather(t["query"])
        if not data["sources"] or sum(len(s["text"]) for s in data["sources"]) < 1500:
            raise RuntimeError("Not enough source material")
        (out / "research.json").write_text(json.dumps(data, indent=2))
        feedback, script, check = "", None, None
        for attempt in range(1, settings.MAX_SCRIPT_ATTEMPTS + 1):
            script = write_script(t["topic"], t["angle"], data["sources"], feedback, script)
            wc = word_count(script)
            check = fact_check(script, data["sources"])
            log.info("Attempt %d: %d words, verdict=%s", attempt, wc, check["verdict"])
            if check["verdict"] == "pass" and 700 <= wc <= 1300:
                break
                        problems = []
            unsupported = check.get("unsupported", [])
            if unsupported:
                problems.append("Unsupported claims: " + "; ".join(unsupported))
            if not 700 <= wc <= 1300:
                problems.append(f"Length is {wc} words but must be 700 to 1300.")
            feedback = "\n".join(problems) or "Fact-check failed. Remove anything not in the sources."
                + ". Use only facts stated in the sources. "
                + "Do not add numbers, materials, colors or causes not in the sources."
            )
        else:
            raise RuntimeError(f"Script failed fact-check/length: {check}")
        script["fact_check"] = check
        (out / "script.json").write_text(json.dumps(script, indent=2))
        db.update(conn, vid, script=json.dumps(script),
                  sources=[{"title": s["title"], "url": s["url"], "license": s["license"]} for s in data["sources"]])
        log.info("Saved to %s", out)
    except Exception as e:
        db.update(conn, vid, error=str(e), upload_status="failed")
        log.exception("Content step failed")
        sys.exit(1)


if __name__ == "__main__":
    run()
