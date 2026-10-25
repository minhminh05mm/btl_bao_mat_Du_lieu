"""The runner must not turn operational failures into successful access denials."""
import httpx

from tests.scenarios import Suite


class RespondingClient:
    def __init__(self, response):
        self.response = response

    def request(self, *args, **kwargs):
        return self.response


def evaluate(response, **expected):
    suite = Suite(RespondingClient(response), operations=None)
    suite.request("unit", "harness", "Independent expected decision", "alice", "GET", "/documents/x/download",
                  **expected)
    return suite.records[0]


def test_a_service_failure_is_not_a_policy_denial():
    response = httpx.Response(503, json={"detail": {"reason": "SERVICE_UNAVAILABLE"}})
    assert not evaluate(response, allow=False, reason="OWNER_OR_LABEL")["passed"]


def test_a_denied_download_must_not_contain_a_plaintext_error_body():
    response = httpx.Response(503, text="SENSITIVE-CONTENT-THAT-MUST-NOT-BE-RETURNED")
    assert not evaluate(response, allow=False, statuses=[503])["passed"]


def test_denied_metadata_must_not_expose_resource_fields():
    response = httpx.Response(403, json={"detail": {"reason": "ROLE"}, "title": "Private title"})
    assert not evaluate(response, allow=False, reason="ROLE")["passed"]


def test_access_granted_against_deny_oracle_fails():
    response = httpx.Response(200, content=b"test-file", headers={"X-Request-ID": "r-unit"})
    assert not evaluate(response, allow=False)["passed"]


def test_clean_deny_with_expected_reason_passes():
    response = httpx.Response(403, json={"detail": {"reason": "ROLE", "request_id": "r-unit"}})
    assert evaluate(response, allow=False, reason="ROLE")["passed"]
