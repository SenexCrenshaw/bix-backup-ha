from __future__ import annotations

import json
from pathlib import Path


def test_hacs_manifest_keys() -> None:
    payload = json.loads((Path(__file__).resolve().parent.parent / "hacs.json").read_text(encoding="utf-8"))
    assert payload["name"] == "BIX Backup"
    assert payload["zip_release"] is True
    assert payload["filename"] == "bix_backup.zip"
