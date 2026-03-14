from __future__ import annotations

from pathlib import Path
import unittest


class FrontendPanelTests(unittest.TestCase):
    def test_panel_asset_exists_and_registers_custom_element(self) -> None:
        panel = (
            Path(__file__).resolve().parent.parent
            / "custom_components"
            / "bix_backup"
            / "frontend"
            / "bix-backup-panel.js"
        ).read_text(encoding="utf-8")

        self.assertIn('customElements.define("bix-backup-panel"', panel)
        self.assertIn("Dynamic Home Assistant view for BIX entities and actions.", panel)
        self.assertIn('this._hass.callService("button", "press"', panel)


if __name__ == "__main__":
    unittest.main()
