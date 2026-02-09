#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "spec" / "retention_contract.schema.json"
EXAMPLES_PATH = ROOT / "spec" / "retention_contract_examples.json"


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(1)


def main() -> None:
    if not SCHEMA_PATH.exists():
        fail(f"Schema not found: {SCHEMA_PATH}")
    if not EXAMPLES_PATH.exists():
        fail(f"Examples not found: {EXAMPLES_PATH}")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    examples = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))

    if not isinstance(examples, list):
        fail("Examples file must be a JSON array.")
    if len(examples) < 5:
        fail("Examples must contain at least 5 templates.")

    required = set(schema.get("required", []))
    allowed_domains = set(schema["properties"]["domain"]["enum"])
    allowed_slots = set(
        schema["properties"]["slot_constraints"]["patternProperties"]
        .keys()
    )
    # patternProperties has one regex key, build explicit slot set from required_slots enum.
    allowed_slots = set(schema["properties"]["required_slots"]["items"]["enum"])

    id_seen = set()
    version_re = re.compile(r"^v[0-9]+\.[0-9]+$")

    for i, item in enumerate(examples, start=1):
        if not isinstance(item, dict):
            fail(f"Template #{i} is not an object.")

        missing = required - set(item.keys())
        if missing:
            fail(f"Template #{i} missing required keys: {sorted(missing)}")

        contract_id = item["contract_id"]
        if contract_id in id_seen:
            fail(f"Duplicate contract_id: {contract_id}")
        id_seen.add(contract_id)

        version = item["version"]
        if not version_re.match(version):
            fail(f"Invalid version format in {contract_id}: {version}")

        domain = item["domain"]
        if domain not in allowed_domains:
            fail(f"Invalid domain in {contract_id}: {domain}")

        required_slots = item["required_slots"]
        if not required_slots:
            fail(f"required_slots is empty in {contract_id}")
        if not set(required_slots).issubset(allowed_slots):
            fail(f"Unknown slot in required_slots of {contract_id}")

        slot_constraints = item["slot_constraints"]
        for slot in required_slots:
            if slot not in slot_constraints:
                fail(f"Missing slot constraint for required slot '{slot}' in {contract_id}")
            sc = slot_constraints[slot]
            if sc["min_coverage_ratio"] < 0 or sc["min_coverage_ratio"] > 1:
                fail(f"Invalid min_coverage_ratio for slot '{slot}' in {contract_id}")
            if sc["min_items"] < 0:
                fail(f"Invalid min_items for slot '{slot}' in {contract_id}")

        lc = item["length_constraints"]
        if lc["per_cluster_min_tokens"] > lc["per_cluster_max_tokens"]:
            fail(f"per_cluster_min_tokens > per_cluster_max_tokens in {contract_id}")
        if lc["global_token_budget"] < lc["per_cluster_min_tokens"]:
            fail(f"global_token_budget too small in {contract_id}")

        vp = item["validation_policy"]
        if vp["max_rewrite_rounds"] < 1:
            fail(f"max_rewrite_rounds must be >= 1 in {contract_id}")

    print("[PASS] Retention contract examples passed structural validation.")


if __name__ == "__main__":
    main()
