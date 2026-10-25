"""Run actual integration groups and print only redacted outcome summaries."""
import argparse
import json

from lab.client import LabClient
from lab import operations
from tests import scenarios


GROUPS = {
    "access": scenarios._basic, "identity": scenarios._identity, "grants": scenarios._grants,
    "context": scenarios._context, "revocation": scenarios._revocation,
    "labels": scenarios._label_change, "faults": scenarios._faults,
    "retention": scenarios._retention, "alerts": scenarios._alerts,
    "storage": scenarios._storage, "restore": scenarios._restore, "isolation": scenarios._isolation,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--groups", default="oracle", help="Comma-separated groups; all includes restore")
    parser.add_argument("--oracle-mode", choices=["B0", "B1"], default="B1")
    args = parser.parse_args()
    selected = args.groups.split(",")
    if selected == ["all"]:
        selected = ["oracle", *GROUPS]
    client = LabClient()
    suite = scenarios.Suite(client, operations)
    try:
        for group in selected:
            start = len(suite.records)
            if group == "oracle":
                suite.records.extend(scenarios.run_oracle(client, operations, mode=args.oracle_mode))
            elif group in GROUPS:
                suite.group(group, lambda function=GROUPS[group]: function(suite))
            else:
                parser.error(f"Unknown group: {group}")
            records = suite.records[start:]
            print(json.dumps({"group": group, "count": len(records),
                "passed": sum(record["passed"] for record in records),
                "failures": [{"id": record["id"], "expected": record["expected"],
                              "actual": record["actual"], "evidence": record["evidence"]}
                             for record in records if not record["passed"]]}, ensure_ascii=False), flush=True)
    finally:
        client.close()
    return 0 if all(record["passed"] for record in suite.records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
