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
        self.assertIn("native Home Assistant cards and theming", panel)
        self.assertIn('type: "entities"', panel)
        self.assertIn('type: "button"', panel)
        self.assertIn('type: "glance"', panel)

    def test_init_registers_panel_with_custom_panel_config_shape(self) -> None:
        init_py = (
            Path(__file__).resolve().parent.parent
            / "custom_components"
            / "bix_backup"
            / "__init__.py"
        ).read_text(encoding="utf-8")

        self.assertIn('"_panel_custom"', init_py)
        self.assertIn('"module_url": PANEL_STATIC_URL', init_py)
        self.assertIn('"embed_iframe": False', init_py)
        self.assertIn('"trust_external": True', init_py)


if __name__ == "__main__":
    unittest.main()
