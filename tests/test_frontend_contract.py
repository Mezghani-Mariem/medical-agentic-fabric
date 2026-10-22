"""Static integration checks; these do not claim to replace a browser test."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from uuid import UUID

from app.input_checks import check_inputs
from app.validation import validate

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.local_assets = []
        self.upload_names = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "script" and "src" in attrs:
            self.local_assets.append(attrs["src"])
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.local_assets.append(attrs["href"])
        if tag == "input" and attrs.get("type") == "file":
            self.upload_names.append(attrs["name"])


def test_dashboard_controls_and_local_assets_exist():
    page = Page()
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    page.feed(html)
    assert len(page.ids) == len(set(page.ids)), "Duplicate element IDs"
    controller = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    controls = set(re.findall(r'\$\("([a-z-]+)"\)', controller))
    assert controls <= set(page.ids)
    assert set(page.upload_names) == {"ecg", "report"}
    assert all((ROOT / "frontend" / name).is_file() for name in page.local_assets)
    assert "Prototype pédagogique, non diagnostic" in html
    assert "preuve locale simulée, intégration Fabric non démontrée" in html
    for path in (ROOT / "frontend").glob("*.js"):
        for target in re.findall(r'from "(\./[^"]+)"', path.read_text(encoding="utf-8")):
            assert (path.parent / target).is_file()


def test_mock_fixture_matches_python_decision_and_eight_artifact_contract():
    data = json.loads((ROOT / "frontend/fixtures/demo_case.json").read_text(encoding="utf-8"))
    assert data == json.loads((ROOT / "docs/api_example.json").read_text(encoding="utf-8"))
    checked = check_inputs((ROOT / "samples/ecg_valid.csv").read_bytes(),
                           (ROOT / "samples/report_valid.txt").read_bytes())
    assert checked["valid"]
    assert data["validation"] == validate(data["prediction"], {"valid": True}, report_text=checked["report_clean"])
    assert data["ledger_mode"] == "MOCK"
    UUID(data["case_id"])
    assert [item["type"] for item in data["artifacts"]] == [
        "raw_ecg", "raw_report", "processed", "features", "prediction", "validation", "explanation", "final"]
    parent = None
    for item in data["artifacts"]:
        UUID(item["artifact_id"])
        assert item["parent_id"] == parent
        assert re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
        assert item["tx_id"].startswith("MOCK-")
        parent = item["artifact_id"]
