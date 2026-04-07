import json
from datetime import datetime, timezone
from buffer import ReadingBuffer


def test_store_and_retrieve(tmp_db):
    buf = ReadingBuffer(tmp_db)
    payload = {"zone_id": "zone-01", "sensor_type": "moisture", "value": 42.3}
    ts = "2026-04-07T12:00:00Z"
    row_id = buf.store("farm/zone-01/sensors/moisture", payload, ts)
    unsent = buf.get_unsent()
    assert len(unsent) == 1
    assert unsent[0][0] == row_id
    assert unsent[0][1] == "farm/zone-01/sensors/moisture"
    assert json.loads(unsent[0][2])["value"] == 42.3
    buf.close()


def test_mark_sent_removes_from_unsent(tmp_db):
    buf = ReadingBuffer(tmp_db)
    row_id = buf.store("farm/zone-01/sensors/ph", {"value": 6.8}, "2026-04-07T12:00:00Z")
    buf.mark_sent(row_id)
    assert len(buf.get_unsent()) == 0
    buf.close()


def test_flush_chronological_order(tmp_db):
    buf = ReadingBuffer(tmp_db)
    # Store out of order
    buf.store("t", {"v": 3}, "2026-04-07T12:03:00Z")
    buf.store("t", {"v": 1}, "2026-04-07T12:01:00Z")
    buf.store("t", {"v": 2}, "2026-04-07T12:02:00Z")
    unsent = buf.get_unsent()
    values = [json.loads(r[2])["v"] for r in unsent]
    assert values == [1, 2, 3], "Must flush in chronological order"
    buf.close()


def test_bulk_insert(tmp_db):
    buf = ReadingBuffer(tmp_db)
    for i in range(1000):
        buf.store("t", {"v": i}, f"2026-04-07T12:{i // 60:02d}:{i % 60:02d}Z")
    assert len(buf.get_unsent(limit=1000)) == 1000
    buf.close()


def test_get_unsent_limit(tmp_db):
    buf = ReadingBuffer(tmp_db)
    for i in range(10):
        buf.store("t", {"v": i}, f"2026-04-07T12:00:{i:02d}Z")
    assert len(buf.get_unsent(limit=5)) == 5
    buf.close()


def test_table_created_on_init(tmp_db):
    buf = ReadingBuffer(tmp_db)
    # Table should exist — verify by querying
    unsent = buf.get_unsent()
    assert unsent == []
    buf.close()
