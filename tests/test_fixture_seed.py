"""Unit boundaries only: spies do not replace the live Transit integration test.

The real seed function is exercised with captured SQL and an encryption spy to
detect plaintext persistence. T21 and T23 still verify the real KMS and restore.
"""
import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import config, db
from app.fixture_data import fixture_payload


class CapturedConnection:
    def __init__(self, already_seeded=False):
        self.calls = []
        self.already_seeded = already_seeded
        self.answer = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=None):
        self.calls.append((query, params))
        self.answer = None
        if "WHERE key='seed_version'" in query:
            self.answer = {"seed_version": "1"} if self.already_seeded else None
        if "count(*) AS n FROM principals" in query:
            self.answer = {"n": 0}
        return self

    def fetchone(self):
        return self.answer


def prepare_seed(monkeypatch, tmp_path, already_seeded=False):
    (tmp_path/"pki").mkdir()
    (tmp_path/"pki"/"registry.json").write_text(json.dumps({
        user: {"serial": f"{i:02X}"} for i, (user, _, _) in enumerate(db.USERS, 1)
    }), encoding="utf-8")
    monkeypatch.setattr(config, "RUNTIME", tmp_path)
    connection = CapturedConnection(already_seeded)
    monkeypatch.setattr(db, "connect", lambda: connection)
    encrypted = []

    def encrypt_spy(operation, plaintext):
        assert operation == "encrypt"
        encrypted.append(plaintext)
        return "vault:v1:unit-spy-"+hashlib.sha256(plaintext).hexdigest()
    monkeypatch.setattr(db, "transit", encrypt_spy)
    return connection, encrypted


def test_seed_persists_transit_output_and_digest_without_plaintext(monkeypatch, tmp_path):
    connection, encrypted = prepare_seed(monkeypatch, tmp_path)
    db.bootstrap()
    manifest = json.loads((Path(__file__).resolve().parents[1]/"fixtures"/"dataset-manifest.json").read_text(encoding="utf-8"))
    reviewed = {row["id"]: row for row in manifest["items"]}
    inserts = [(q, p) for q, p in connection.calls if q.startswith("INSERT INTO documents(")]
    assert len(inserts) == len(encrypted) == 20
    for query, values in inserts:
        columns = query.split("(", 1)[1].split(")", 1)[0].split(",")
        row = dict(zip(columns, values))
        baseline = reviewed[row["id"]]
        assert row["title"] == baseline["title"]
        assert row["owner_id"] == baseline["owner_id"]
        assert row["label"] == baseline["baseline_label"]
        assert row["sha256"] == baseline["sha256"]
        assert row["ciphertext"] == "vault:v1:unit-spy-"+baseline["sha256"]
        assert fixture_payload(row["id"]) in encrypted
        assert row["version"] == (2 if row["label"] == "restricted" else 1)
    serialized = repr(connection.calls)
    assert "BMDL synthetic fixture " not in serialized
    assert "4.800.000 đồng/gói" not in serialized


def test_restart_does_not_replace_existing_documents(monkeypatch, tmp_path):
    connection, encrypted = prepare_seed(monkeypatch, tmp_path, already_seeded=True)
    db.bootstrap()
    assert not encrypted
    assert not any("INSERT INTO" in q or "TRUNCATE" in q for q, _ in connection.calls)


def test_catalog_endpoint_stays_local_and_excludes_document_contents():
    from lab.web import app
    with TestClient(app) as client:
        response = client.get("/lab/dataset")
        assert response.status_code == 200
        assert len(response.json()["items"]) == 20
        assert "synthetic_example" not in response.text
        assert "4.800.000" not in response.text
        assert client.get("/lab/dataset", headers={"host": "untrusted.example"}).status_code == 400


def test_business_metadata_excludes_fixture_contents_and_storage_material():
    from app.main import metadata
    row = {key: "placeholder" for key in ["id", "title", "owner_id", "department", "label", "version", "retention_until", "legal_hold"]}
    row.update(ciphertext="vault:v1:protected", content=fixture_payload("A-C01").decode(),
               synthetic_example="private example", sha256="private digest")
    result = metadata(row)
    assert not {"ciphertext", "content", "synthetic_example", "sha256"} & result.keys()
