from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BixBackupCoordinator


SUMMARY_SENSORS = (
    ("connected_hosts", "Connected Hosts"),
    ("running_jobs", "Running Jobs"),
    ("jobs_failed_24h", "Failed Jobs (24h)"),
    ("open_alerts_total", "Open Alerts"),
    ("open_alerts_critical", "Open Critical Alerts"),
    ("open_alerts_warning", "Open Warning Alerts"),
    ("open_alerts_info", "Open Info Alerts"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BixBackupCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [BixSummarySensor(coordinator, key, label) for key, label in SUMMARY_SENSORS]

    if coordinator.enable_host_entities:
        for host in coordinator.data.get("hosts", []):
            host_id = str(host.get("id", "")).strip()
            if host_id:
                entities.append(BixHostLastSeenSensor(coordinator, host_id))

    if coordinator.enable_job_entities:
        for job in coordinator.data.get("jobs", []):
            job_id = str(job.get("job_id", "")).strip()
            if not job_id:
                continue
            entities.extend(
                [
                    BixJobSensor(coordinator, job_id, "last_execution_status", "Last Execution Status"),
                    BixJobSensor(coordinator, job_id, "last_execution_time", "Last Execution Time"),
                    BixJobSensor(coordinator, job_id, "last_success_time", "Last Success Time"),
                    BixJobSensor(coordinator, job_id, "last_failure_time", "Last Failure Time"),
                    BixJobSensor(coordinator, job_id, "last_duration_ms", "Last Duration (ms)"),
                    BixJobSensor(coordinator, job_id, "last_backup_total_files", "Last Backup Total Files"),
                    BixJobSensor(coordinator, job_id, "last_backup_total_bytes", "Last Backup Total Bytes"),
                    BixJobSensor(coordinator, job_id, "last_backup_data_added_bytes", "Last Backup Data Added"),
                    BixJobSensor(coordinator, job_id, "open_alert_count", "Open Alert Count"),
                ]
            )

    async_add_entities(entities)


class BixSummarySensor(CoordinatorEntity[BixBackupCoordinator], SensorEntity):
    def __init__(self, coordinator: BixBackupCoordinator, key: str, label: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"BIX {label}"
        self._attr_unique_id = f"bix_summary_{key}"

    @property
    def native_value(self) -> Any:
        summary = self.coordinator.data.get("summary", {})
        if isinstance(summary, dict):
            return summary.get(self._key)
        return None


class BixHostLastSeenSensor(CoordinatorEntity[BixBackupCoordinator], SensorEntity):
    def __init__(self, coordinator: BixBackupCoordinator, host_id: str) -> None:
        super().__init__(coordinator)
        self._host_id = host_id
        self._attr_name = f"BIX Host {host_id} Last Seen"
        self._attr_unique_id = f"bix_host_{host_id}_last_seen"

    @property
    def native_value(self) -> Any:
        host = self.coordinator.get_host(self._host_id)
        if host is None:
            return None
        return host.get("last_seen")

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.get_host(self._host_id) is not None


class BixJobSensor(CoordinatorEntity[BixBackupCoordinator], SensorEntity):
    def __init__(self, coordinator: BixBackupCoordinator, job_id: str, key: str, label: str) -> None:
        super().__init__(coordinator)
        self._job_id = job_id
        self._key = key
        self._label = label
        self._attr_name = f"BIX Job {coordinator.get_job_label(job_id)} {label}"
        self._attr_unique_id = f"bix_job_{job_id}_{key}"
        if key in {"last_backup_total_bytes", "last_backup_data_added_bytes"}:
            self._attr_native_unit_of_measurement = "B"

    @property
    def native_value(self) -> Any:
        job = self.coordinator.get_job(self._job_id)
        if job is None:
            return None
        return job.get(self._key)

    @property
    def name(self) -> str | None:
        return f"BIX Job {self.coordinator.get_job_label(self._job_id)} {self._label}"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.get_job(self._job_id) is not None
