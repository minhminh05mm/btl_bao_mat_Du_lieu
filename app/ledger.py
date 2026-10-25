"""Durable mutation outbox and operator-side reconciliation journal.

The database mutation and outbox row commit together. Journal append is fsynced
before a mutation endpoint returns success. Startup retries any pending outbox.
Duplicate event IDs are harmless to replay consumers.
"""
import fcntl
import json
import os
import time
import uuid

from psycopg.types.json import Jsonb

from . import config


def enqueue(conn, kind, entity_id, payload, actor_id):
    event = {
        "event_id": str(uuid.uuid4()), "at": time.time(),
        "kind": kind.split("_", 1)[0], "operation": kind,
        "id": str(entity_id), "actor": actor_id, "changes": payload,
    }
    conn.execute(
        "INSERT INTO ledger_outbox(event_id,event) VALUES (%s,%s)",
        (event["event_id"], Jsonb(event)),
    )
    return event


def flush(conn):
    # Separate committed transaction; no secrets or document contents are journaled.
    with conn.transaction():
        rows = conn.execute(
            "SELECT event_id,event FROM ledger_outbox WHERE delivered=false ORDER BY sequence FOR UPDATE"
        ).fetchall()
        if not rows:
            return
        path = config.RUNTIME / "ledger/events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                for row in rows:
                    stream.write(json.dumps(row["event"], ensure_ascii=False, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        conn.execute("UPDATE ledger_outbox SET delivered=true WHERE event_id=ANY(%s)",
                     ([r["event_id"] for r in rows],))
