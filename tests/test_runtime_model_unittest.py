from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "bix_backup"
    / "runtime_model.py"
)
SPEC = importlib.util.spec_from_file_location("bix_backup_runtime_model", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime_model = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime_model)


DISCOVERY_PAYLOAD = {
    "schema_version": 1,
    "transport": {
        "supported_events": ["job", "alerts", "config"],
        "poll_fallback_seconds": 45,
    },
    "capabilities": {
        "actions_enabled": True,
        "job_actions": ["run_backup"],
        "alert_actions": ["ack", "resolve"],
    },
    "entity_catalog": {
        "host": [
            {"key": "connected", "type": "binary_sensor"},
            {"key": "running", "type": "binary_sensor"},
            {"key": "last_seen", "type": "sensor"},
        ],
        "job": [
            {"key": "enabled", "type": "binary_sensor"},
            {"key": "running", "type": "binary_sensor"},
            {"key": "last_execution_status", "type": "sensor"},
            {"key": "last_backup_total_files", "type": "sensor"},
            {"key": "last_backup_total_bytes", "type": "sensor"},
            {"key": "last_backup_data_added_bytes", "type": "sensor"},
            {"key": "open_alert_count", "type": "sensor"},
        ],
        "alert_summary": [
            {"key": "open_total", "type": "sensor"},
            {"key": "open_critical", "type": "sensor"},
            {"key": "open_warning", "type": "sensor"},
            {"key": "open_info", "type": "sensor"},
        ],
    },
    "inventory": {
        "jobs": [
            {"job_id": "job-a", "job_name": "Nightly", "host_id": "host-1"},
            {"job_id": "job-b", "job_name": "Weekly", "host_id": "host-2"},
        ]
    },
}

STATE_PAYLOAD = {
    "schema_version": 1,
    "hosts": [
        {"id": "host-1", "connected": True, "running": False, "last_seen": "2026-03-14T09:00:00Z"},
        {"id": "host-2", "connected": False, "running": False, "last_seen": "2026-03-13T09:00:00Z"},
    ],
    "jobs": [
        {
            "job_id": "job-a",
            "job_name": "Nightly",
            "host_id": "host-1",
            "enabled": True,
            "running": False,
            "last_execution_status": "success",
            "last_backup_total_files": 12,
            "last_backup_total_bytes": 2048,
            "last_backup_data_added_bytes": 256,
            "open_alert_count": 0,
        }
    ],
    "alerts": [
        {"id": "alert-1", "job_id": "job-a", "severity": "warning", "can_ack": True, "can_resolve": True}
    ],
    "summary": {
        "connected_hosts": 1,
        "running_jobs": 0,
        "jobs_failed_24h": 0,
        "open_alerts_total": 1,
        "open_alerts_critical": 0,
        "open_alerts_warning": 1,
        "open_alerts_info": 0,
    },
}


class RuntimeModelTests(unittest.TestCase):
    def test_transport_and_capabilities_come_from_discovery(self) -> None:
        self.assertEqual(runtime_model.supported_ws_events(DISCOVERY_PAYLOAD), ("job", "alerts", "config"))
        self.assertEqual(runtime_model.discovery_poll_fallback_seconds(DISCOVERY_PAYLOAD, 30), 45)
        self.assertEqual(runtime_model.discovery_job_actions(DISCOVERY_PAYLOAD), ("run_backup",))
        self.assertEqual(runtime_model.discovery_alert_actions(DISCOVERY_PAYLOAD), ("ack", "resolve"))

    def test_entity_catalog_drives_keys_and_includes_backup_metrics(self) -> None:
        self.assertEqual(runtime_model.host_binary_keys(DISCOVERY_PAYLOAD), ("connected", "running"))
        self.assertEqual(runtime_model.host_sensor_keys(DISCOVERY_PAYLOAD), ("last_seen",))
        self.assertEqual(runtime_model.job_binary_keys(DISCOVERY_PAYLOAD), ("enabled", "running"))
        self.assertEqual(
            runtime_model.job_sensor_keys(DISCOVERY_PAYLOAD),
            (
                "last_execution_status",
                "last_backup_total_files",
                "last_backup_total_bytes",
                "last_backup_data_added_bytes",
                "open_alert_count",
            ),
        )
        self.assertEqual(
            runtime_model.summary_sensor_keys(DISCOVERY_PAYLOAD),
            (
                "connected_hosts",
                "running_jobs",
                "jobs_failed_24h",
                "open_alerts_total",
                "open_alerts_critical",
                "open_alerts_warning",
                "open_alerts_info",
            ),
        )

    def test_state_helpers_are_tolerant_and_inventory_is_dynamic(self) -> None:
        self.assertEqual(len(runtime_model.state_hosts(STATE_PAYLOAD)), 2)
        self.assertEqual(len(runtime_model.state_jobs(STATE_PAYLOAD)), 1)
        self.assertEqual(len(runtime_model.state_alerts(STATE_PAYLOAD)), 1)
        self.assertEqual(runtime_model.desired_host_ids(STATE_PAYLOAD), ("host-1", "host-2"))
        self.assertEqual(runtime_model.desired_job_ids(STATE_PAYLOAD), ("job-a",))
        self.assertEqual(runtime_model.desired_alert_ids(STATE_PAYLOAD), ("alert-1",))
        self.assertEqual(runtime_model.reconcile_ids(("job-a",), ("job-a", "job-b")), (("job-b",), ()))
        self.assertEqual(runtime_model.reconcile_ids(("alert-1", "alert-2"), ("alert-2",)), ((), ("alert-1",)))

    def test_job_resolution_uses_job_name_and_host_id_without_repo_id(self) -> None:
        self.assertEqual(runtime_model.job_name("job-a", STATE_PAYLOAD, DISCOVERY_PAYLOAD), "Nightly")
        self.assertEqual(runtime_model.job_label("job-a", STATE_PAYLOAD, DISCOVERY_PAYLOAD), "Nightly (host-1)")
        self.assertEqual(runtime_model.job_name("job-b", STATE_PAYLOAD, DISCOVERY_PAYLOAD), "Weekly")
        self.assertEqual(runtime_model.job_label("job-b", STATE_PAYLOAD, DISCOVERY_PAYLOAD), "Weekly (host-2)")

    def test_entity_keys_preserve_full_metric_names(self) -> None:
        self.assertEqual(runtime_model.host_entity_key("host-1", "last_seen"), "host:host-1:last_seen")
        self.assertEqual(
            runtime_model.job_entity_key("job-a", "last_execution_status"),
            "job:job-a:last_execution_status",
        )

    def test_helpers_tolerate_missing_sections(self) -> None:
        self.assertEqual(runtime_model.supported_ws_events({}), ("host", "job", "alerts", "config"))
        self.assertEqual(runtime_model.discovery_poll_fallback_seconds({}, 30), 30)
        self.assertEqual(
            runtime_model.summary_sensor_keys({}),
            (
                "connected_hosts",
                "running_jobs",
                "jobs_failed_24h",
                "open_alerts_total",
                "open_alerts_critical",
                "open_alerts_warning",
                "open_alerts_info",
            ),
        )
        self.assertEqual(runtime_model.desired_job_ids({}), ())


if __name__ == "__main__":
    unittest.main()
