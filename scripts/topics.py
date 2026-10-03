import json
from config.settings import SEEDS_PATH
from scripts import db

def pick_topic(conn):
    seeds = json.loads(SEEDS_PATH.read_text())
    for t in seeds:
        if not db.topic_used(conn, t["topic"]):
            return t
    raise RuntimeError("No unused topics left. Add more to data/topic_seeds.json")
