from __future__ import annotations

import json
from pathlib import Path


def test_hacs_declares_domain() -> None:
    payload = json.loads((Path(__file__).resolve().parent.parent / "hacs.json").read_text(encoding="utf-8"))
    assert "bix_backup" in payload["domains"]
