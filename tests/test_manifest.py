from __future__ import annotations

import json
from pathlib import Path


def test_manifest_has_expected_domain() -> None:
    manifest_path = (
        Path(__file__).resolve().parent.parent
        / "custom_components"
        / "bix_backup"
        / "manifest.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["domain"] == "bix_backup"
    assert payload["config_flow"] is True
