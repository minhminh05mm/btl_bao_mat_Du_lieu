"""Review the business dataset independently of PostgreSQL and encryption I/O."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from app.fixture_data import (CLASSIFICATION_RULES, DATASET_VERSION, dataset_catalog,
                              dataset_manifest, fixture_definition, fixture_payload)

ROOT = Path(__file__).resolve().parents[1]


class BusinessFixtureTests(unittest.TestCase):
    def test_contract_ids_labels_and_owners_are_preserved(self):
        catalog = dataset_catalog()
        expected = {f"{d}-{letter}{i:02d}" for d in "AB"
                    for letter, count in [("I", 5), ("C", 3), ("R", 2)]
                    for i in range(1, count+1)}
        self.assertEqual({doc["id"] for doc in catalog["items"]}, expected)
        for dept, owners in [("A", ["alice", "anna", "adam"]), ("B", ["bob", "bea", "brian"])]:
            rows = [doc for doc in catalog["items"] if doc["department"] == dept]
            self.assertEqual([sum(x["baseline_label"] == v for x in rows)
                              for v in ["internal", "confidential", "restricted"]], [5, 3, 2])
            for letter, expected_owners in [("I", owners+[owners[0], owners[1]]), ("C", owners), ("R", [owners[0], owners[2]])]:
                self.assertEqual([fixture_definition(f"{dept}-{letter}{i:02d}")["owner_id"]
                                  for i in range(1, len(expected_owners)+1)], expected_owners)

    def test_each_document_is_meaningful_utf8_and_within_upload_limit(self):
        titles = []
        for doc in dataset_catalog()["items"]:
            payload = fixture_payload(doc["id"])
            body = payload.decode("utf-8", errors="strict")
            titles.append(doc["title"])
            self.assertTrue(12000 <= len(payload) <= 32000 < 1024*1024)
            self.assertIn(doc["title"].removesuffix(".txt"), body)
            self.assertIn(doc["classification_reason"], body)
            self.assertIn(f"Chủ hồ sơ thử nghiệm: {doc['owner_id']}", body)
            self.assertIn("không phản ánh cá nhân hoặc tổ chức thực", body)
            self.assertEqual(body.count("Hạng mục "+doc["id"]+"-HM"), 24)
            self.assertNotIn("Synthetic document", doc["title"])
            self.assertTrue(doc["title"].endswith(".txt"))
        self.assertEqual(len(set(titles)), 20)

    def test_concrete_content_supports_distinct_classification(self):
        procedure = fixture_payload("A-I01").decode()
        quote = fixture_payload("A-C01").decode()
        exception = fixture_payload("A-R01").decode()
        recovery = fixture_payload("B-R02").decode()
        self.assertIn("kiểm tra đủ mô tả nhu cầu", procedure)
        self.assertNotIn("4.800.000", procedure)
        self.assertIn("4.800.000 đồng/gói", quote)
        self.assertIn("chiết khấu ngoại lệ tối đa 7 phần trăm", exception)
        self.assertIn("kiểm tra trạng thái thu hồi rồi mới", recovery)
        self.assertIn("không có mã khai thác", fixture_payload("B-R01").decode())

    def test_published_manifest_matches_exact_payload_hashes(self):
        committed = json.loads((ROOT/"fixtures"/"dataset-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(committed, dataset_manifest())
        self.assertEqual(committed["dataset_version"], DATASET_VERSION)
        self.assertEqual(len({row["sha256"] for row in committed["items"]}), 20)
        for row in committed["items"]:
            self.assertEqual(row["sha256"], hashlib.sha256(fixture_payload(row["id"])).hexdigest())

    def test_operator_catalog_does_not_serve_plaintext_examples(self):
        catalog = dataset_catalog()
        serialized = json.dumps(catalog, ensure_ascii=False)
        self.assertNotIn("4.800.000", serialized)
        self.assertNotIn("7 phần trăm", serialized)
        for row in catalog["items"]:
            self.assertFalse({"content", "payload", "content_b64", "synthetic_example", "tasks", "ciphertext"} & row.keys())
            self.assertNotIn(fixture_payload(row["id"]).decode(), serialized)

    def test_grant_description_does_not_claim_single_use(self):
        rule = CLASSIFICATION_RULES["restricted"]
        self.assertNotIn("từng lần sử dụng", rule["criterion"])
        for term in ["người", "phiên bản", "hành động", "thời hạn"]:
            self.assertIn(term, rule["access"])
        self.assertEqual({x["retention_days"] for x in CLASSIFICATION_RULES.values()}, {30, 90, 180})

    def test_catalog_edits_do_not_change_server_baseline(self):
        catalog = dataset_catalog()
        catalog["items"][0]["baseline_label"] = "restricted"
        catalog["rules"]["internal"]["name"] = "changed"
        self.assertEqual(fixture_definition("A-I01")["baseline_label"], "internal")
        self.assertEqual(dataset_catalog()["rules"]["internal"]["name"], "Nội bộ")
        with self.assertRaises(ValueError):
            fixture_payload("U-not-a-reviewed-fixture")

    def test_payload_is_stable_across_process_and_hash_seed(self):
        expected = hashlib.sha256(fixture_payload("A-C01")).hexdigest()
        env = dict(os.environ, PYTHONHASHSEED="17", PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run([sys.executable, "-B", "-c",
            "import hashlib; from app.fixture_data import fixture_payload; print(hashlib.sha256(fixture_payload('A-C01')).hexdigest())"],
            cwd=ROOT, env=env, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), expected)


if __name__ == "__main__":
    unittest.main()
