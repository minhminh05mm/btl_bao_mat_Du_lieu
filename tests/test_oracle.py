import json
import os

import pytest

from tests.scenarios import ORACLE_PATH, run_suite


def test_reviewed_oracle_has_independent_balanced_labels():
    source = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
    cases = source["cases"]
    assert len(cases) >= 40
    assert len({case["id"] for case in cases}) == len(cases)
    assert sum(case["expected"]["allow"] is True for case in cases) >= 20
    assert sum(case["expected"]["allow"] is False for case in cases) >= 20
    for case in cases:
        assert type(case["expected"]["allow"]) is bool
        assert case["expected"]["statuses"]
        assert case["path"].startswith("/")
        assert case.get("mode", "B1") in {"B0", "B1"}


@pytest.mark.skipif(os.getenv("BMDL_RUN_INTEGRATION") != "1",
                    reason="Requires the running isolated lab; set BMDL_RUN_INTEGRATION=1")
def test_real_architecture_scenarios():
    from lab.client import LabClient
    from lab import operations

    client = LabClient()
    try:
        records = run_suite(client, operations)
    finally:
        client.close()
    failures = [record["id"] for record in records if not record["passed"]]
    assert len([record for record in records if record["group"] == "oracle"]) >= 40
    assert not failures, f"Failed scenarios: {failures}"
