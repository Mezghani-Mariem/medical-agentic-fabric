"""The same synthetic byte fixtures are consumed by Python and JavaScript."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from app.input_checks import check_inputs

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "samples/csv_contract_cases.json").read_text(encoding="utf-8"))["cases"]


def fixture_bytes(item, field):
    if f"{field}_hex" in item:
        return bytes.fromhex(item[f"{field}_hex"])
    if f"{field}_parts" in item:
        text = "".join(part if isinstance(part, str) else part["repeat"] * part["count"]
                       for part in item[f"{field}_parts"])
    else:
        text = item.get(field, "Rapport entièrement synthétique.")
    return text.encode("utf-8")


@pytest.mark.parametrize("item", CASES, ids=lambda item: item["id"])
def test_shared_csv_contract(item):
    assert check_inputs(fixture_bytes(item, "ecg"), fixture_bytes(item, "report"))["valid"] is item["valid"]


def test_python_javascript_decisions_match():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is optional; install it to execute cross-language parity.")
    process = subprocess.run([node, "frontend/tests/csv_fixtures.mjs"], cwd=ROOT,
                             capture_output=True, text=True, encoding="utf-8", timeout=60, check=True)
    actual = {result["id"]: result["valid"] for result in json.loads(process.stdout)}
    expected = {item["id"]: check_inputs(fixture_bytes(item, "ecg"), fixture_bytes(item, "report"))["valid"]
                for item in CASES}
    assert actual == expected
