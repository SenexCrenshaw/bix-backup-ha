from __future__ import annotations

from pathlib import Path
import unittest


class SensorSourceTests(unittest.TestCase):
    def test_report_summary_sensors_are_discovery_driven(self) -> None:
        source = (
            Path(__file__).resolve().parent.parent
            / "custom_components"
            / "bix_backup"
            / "sensor.py"
        ).read_text(encoding="utf-8")

        self.assertIn("report_summary_sensor_keys", source)
        self.assertIn("BixReportSummarySensor", source)
        self.assertIn("state_reports(self.coordinator.data)", source)
        self.assertIn("bix_report_summary_", source)


if __name__ == "__main__":
    unittest.main()
