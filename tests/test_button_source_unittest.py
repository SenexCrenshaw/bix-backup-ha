from __future__ import annotations

from pathlib import Path
import unittest


class ButtonSourceTests(unittest.TestCase):
    def test_alert_buttons_publish_alert_metadata(self) -> None:
        source = (
            Path(__file__).resolve().parent.parent
            / "custom_components"
            / "bix_backup"
            / "button.py"
        ).read_text(encoding="utf-8")

        self.assertIn("def _alert_attributes(", source)
        self.assertIn('"alert_id": str(alert.get("id", "")).strip()', source)
        self.assertIn('"severity"', source)
        self.assertIn('"message"', source)
        self.assertIn("extra_state_attributes", source)


if __name__ == "__main__":
    unittest.main()
