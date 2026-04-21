from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BixBackupCoordinator
from .runtime_model import (
    host_entity_key,
    host_sensor_keys,
    job_entity_key,
    job_sensor_keys,
    prettify_key,
    reconcile_ids,
    report_summary_sensor_keys,
    state_reports,
    summary_sensor_keys,
)

SUMMARY_LABELS = {
    "connected_hosts": "Connected Hosts",
    "running_jobs": "Running Jobs",
    "jobs_failed_24h": "Failed Jobs (24h)",
    "open_alerts_total": "Open Alerts",
    "open_alerts_critical": "Open Critical Alerts",
    "open_alerts_warning": "Open Warning Alerts",
    "open_alerts_info": "Open Info Alerts",
}
REPORT_SUMMARY_LABELS = {
    "archived_report_count": "Archived Reports",
    "latest_report_generated_at": "Latest Report Generated",
    "latest_report_trigger": "Latest Report Trigger",
    "latest_report_cadence_label": "Latest Report Cadence",
    "latest_report_delivery_status": "Latest Report Delivery Status",
    "latest_report_total_jobs": "Latest Report Total Jobs",
    "latest_report_open_alerts": "Latest Report Open Alerts",
    "latest_report_critical_alerts": "Latest Report Critical Alerts",
    "latest_report_attention_jobs": "Latest Report Attention Jobs",
}
HOST_LABELS = {
    "last_seen": "Last Seen",
}
JOB_LABELS = {
    "last_execution_status": "Last Execution Status",
    "last_execution_time": "Last Execution Time",
    "last_success_time": "Last Success Time",
    "last_failure_time": "Last Failure Time",
    "last_duration_ms": "Last Duration (ms)",
    "last_backup_total_files": "Last Backup Total Files",
    "last_backup_total_bytes": "Last Backup Total Bytes",
    "last_backup_data_added_bytes": "Last Backup Data Added",
    "open_alert_count": "Open Alert Count",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BixBackupCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: dict[str, SensorEntity] = {}

    summary_entities = [
        BixSummarySensor(coordinator, key, SUMMARY_LABELS.get(key, prettify_key(key)))
        for key in summary_sensor_keys(coordinator.discovery)
    ]
    report_summary_entities = [
        BixReportSummarySensor(coordinator, key, REPORT_SUMMARY_LABELS.get(key, prettify_key(key)))
        for key in report_summary_sensor_keys(coordinator.discovery)
    ]
    async_add_entities(summary_entities + report_summary_entities)

    def _sync_dynamic_entities() -> None:
        desired_keys: set[str] = set()
        new_entities: list[SensorEntity] = []

        if coordinator.enable_host_entities:
            for host_id in coordinator.desired_host_ids():
                for key in host_sensor_keys(coordinator.discovery):
                    entity_key = host_entity_key(host_id, key)
                    desired_keys.add(entity_key)
                    if entity_key in entities:
                        continue
                    new_entities.append(
                        BixHostSensor(coordinator, host_id, key, HOST_LABELS.get(key, prettify_key(key)))
                    )

        if coordinator.enable_job_entities:
            for job_id in coordinator.desired_job_ids():
                for key in job_sensor_keys(coordinator.discovery):
                    entity_key = job_entity_key(job_id, key)
                    desired_keys.add(entity_key)
                    if entity_key in entities:
                        continue
                    new_entities.append(
                        BixJobSensor(coordinator, job_id, key, JOB_LABELS.get(key, prettify_key(key)))
                    )

        if new_entities:
            for entity in new_entities:
                entities[_entity_key(entity)] = entity
            async_add_entities(new_entities)

        _, stale_keys = reconcile_ids(entities.keys(), desired_keys)
        for stale_key in stale_keys:
            entity = entities.pop(stale_key, None)
            if entity is not None:
                hass.async_create_task(entity.async_remove())

    _sync_dynamic_entities()
    entry.async_on_unload(coordinator.async_add_listener(_sync_dynamic_entities))


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


class BixReportSummarySensor(CoordinatorEntity[BixBackupCoordinator], SensorEntity):
    def __init__(self, coordinator: BixBackupCoordinator, key: str, label: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"BIX {label}"
        self._attr_unique_id = f"bix_report_summary_{key}"

    @property
    def native_value(self) -> Any:
        reports = state_reports(self.coordinator.data)
        return reports.get(self._key)


class BixHostSensor(CoordinatorEntity[BixBackupCoordinator], SensorEntity):
    def __init__(self, coordinator: BixBackupCoordinator, host_id: str, key: str, label: str) -> None:
        super().__init__(coordinator)
        self._host_id = host_id
        self._key = key
        self._label = label
        self._attr_name = f"BIX Host {host_id} {label}"
        self._attr_unique_id = f"bix_host_{host_id}_{key}"

    @property
    def native_value(self) -> Any:
        host = self.coordinator.get_host(self._host_id)
        if host is None:
            return None
        return host.get(self._key)

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.get_host(self._host_id) is not None

    @property
    def name(self) -> str | None:
        return f"BIX Host {self._host_id} {self._label}"


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


def _entity_key(entity: SensorEntity) -> str:
    host_id = getattr(entity, "_host_id", None)
    key = getattr(entity, "_key", None)
    if isinstance(host_id, str) and isinstance(key, str):
        return host_entity_key(host_id, key)
    job_id = getattr(entity, "_job_id", None)
    if isinstance(job_id, str) and isinstance(key, str):
        return job_entity_key(job_id, key)
    return getattr(entity, "entity_id", repr(entity))
