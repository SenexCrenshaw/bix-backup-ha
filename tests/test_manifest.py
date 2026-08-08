from __future__ import annotations

import ast
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


def test_ui_events_protocol_matches_controller_contract() -> None:
    const_path = (
        Path(__file__).resolve().parent.parent
        / "custom_components"
        / "bix_backup"
        / "const.py"
    )
    module = ast.parse(const_path.read_text(encoding="utf-8"))
    assignments = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in module.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }
    assert assignments["UI_EVENTS_PROTOCOL_VERSION"] == "ui-events/v2"
