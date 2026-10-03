import json
from scripts import db, topics
from config import settings

def test_dedupe(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    assert not db.topic_used(conn, "How Apollo 13 Survived")
    db.reserve_topic(conn, "How Apollo 13 Survived")
    assert db.topic_used(conn, "How Apollo 13 Survived")
    assert db.topic_used(conn, "how apollo 13 survived!")
    assert db.topic_used(conn, "How Apollo 13 Survived It")
    assert not db.topic_used(conn, "The Voyager Golden Record")

def test_pick_skips_used(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    first = topics.pick_topic(conn)["topic"]
    db.reserve_topic(conn, first)
    assert topics.pick_topic(conn)["topic"] != first

def test_seeds_valid():
    for s in json.loads(settings.SEEDS_PATH.read_text()):
        assert {"topic", "query", "angle"} <= s.keys()
