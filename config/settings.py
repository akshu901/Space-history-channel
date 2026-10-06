import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "content.db"
SEEDS_PATH = ROOT / "data" / "topic_seeds.json"
OUTPUT_DIR = ROOT / "output"
LOG_DIR = ROOT / "logs"

TIMEZONE = os.getenv("TIMEZONE", "America/New_York")
PUBLISH_TIME = os.getenv("PUBLISH_TIME", "18:00")  # local time, 24h

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # secret, never hard-code
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")  # check current free-tier models
CONTACT = os.getenv("CONTACT_EMAIL", "set-your-email@example.com")
USER_AGENT = f"SpaceHistoryBot/0.1 ({CONTACT})"

TARGET_WORDS = 950  # about 6-7 min at ~150 wpm
MAX_SCRIPT_ATTEMPTS = 5
