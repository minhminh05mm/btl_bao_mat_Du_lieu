"""Trusted operator-only schema/fixture utility, with no HTTP bypass endpoint."""
import json
import sys

from .db import bootstrap, connect


def reset_database():
    bootstrap(reset=True)
    with connect() as conn:
        count = conn.execute("SELECT count(*) AS n FROM documents WHERE deleted=false").fetchone()["n"]
    return {"status": "reset", "document_count": count}


if __name__ == "__main__":
    if sys.argv[1:] == ["reset"]:
        print(json.dumps(reset_database()))
    elif sys.argv[1:] in ([], ["init"]):
        bootstrap()
        print(json.dumps({"status": "initialized"}))
    else:
        raise SystemExit("Usage: python -m app.bootstrap [init|reset]")
