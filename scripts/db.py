import json, re, sqlite3, difflib
from datetime import datetime, timezone
from config.settings import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  script TEXT,
  sources TEXT,
  video_file TEXT,
  thumbnail_file TEXT,
  youtube_id TEXT,
  upload_status TEXT DEFAULT 'pending',
  publish_status TEXT DEFAULT 'pending',
  error TEXT
);
"""

def slugify(topic: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")

def connect(path=None):
    conn = sqlite3.connect(str(path or DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn

def topic_used(conn, topic: str, threshold: float = 0.85) -> bool:
    slug = slugify(topic)
    for row in conn.execute("SELECT slug FROM videos"):
        if row["slug"] == slug or difflib.SequenceMatcher(None, slug, row["slug"]).ratio() >= threshold:
            return True
    return False

def reserve_topic(conn, topic: str) -> int:
    """Insert the topic first so a crash mid-run can't cause a repeat."""
    cur = conn.execute(
        "INSERT INTO videos (topic, slug, created_at) VALUES (?,?,?)",
        (topic, slugify(topic), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cur.lastrowid

def update(conn, vid: int, **fields):
    if "sources" in fields and not isinstance(fields["sources"], str):
        fields["sources"] = json.dumps(fields["sources"])
    cols = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE videos SET {cols} WHERE id=?", (*fields.values(), vid))
    conn.commit()
