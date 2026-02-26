from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BixBackupCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BixBackupCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []

    if coordinator.enable_host_entities:
        for host in coordinator.data.get("hosts", []):
            host_id = str(host.get("id", "")).strip()
            if not host_id:
                continue
            entities.append(BixHostBinarySensor(coordinator, host_id, "connected", "Connected"))
            entities.append(BixHostBinarySensor(coordinator, host_id, "running", "Running"))

    if coordinator.enable_job_entities:
        for job in coordinator.data.get("jobs", []):
            job_id = str(job.get("job_id", "")).strip()
            if not job_id:
                continue
            entities.append(BixJobBinarySensor(coordinator, job_id, "enabled", "Enabled"))
            entities.append(BixJobBinarySensor(coordinator, job_id, "running", "Running"))

    async_add_entities(entities)


class BixHostBinarySensor(CoordinatorEntity[BixBackupCoordinator], BinarySensorEntity):
    def __init__(self, coordinator: BixBackupCoordinator, host_id: str, key: str, label: str) -> None:
        super().__init__(coordinator)
        self._host_id = host_id
        self._key = key
        self._attr_name = f"BIX Host {host_id} {label}"
        self._attr_unique_id = f"bix_host_{host_id}_{key}"

    @property
    def is_on(self) -> bool | None:
        host = self.coordinator.get_host(self._host_id)
        if host is None:
            return None
        value = host.get(self._key)
        return bool(value) if isinstance(value, bool) else None

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.get_host(self._host_id) is not None


class BixJobBinarySensor(CoordinatorEntity[BixBackupCoordinator], BinarySensorEntity):
    def __init__(self, coordinator: BixBackupCoordinator, job_id: str, key: str, label: str) -> None:
        super().__init__(coordinator)
        self._job_id = job_id
        self._key = key
        self._attr_name = f"BIX Job {job_id} {label}"
        self._attr_unique_id = f"bix_job_{job_id}_{key}"

    @property
    def is_on(self) -> bool | None:
        job = self.coordinator.get_job(self._job_id)
        if job is None:
            return None
        value = job.get(self._key)
        return bool(value) if isinstance(value, bool) else None

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.get_job(self._job_id) is not None
