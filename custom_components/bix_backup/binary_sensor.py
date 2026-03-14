from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BixBackupCoordinator
from .runtime_model import (
    host_binary_keys,
    host_entity_key,
    job_binary_keys,
    job_entity_key,
    prettify_key,
    reconcile_ids,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BixBackupCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: dict[str, BinarySensorEntity] = {}

    def _sync_dynamic_entities() -> None:
        desired_keys: set[str] = set()
        new_entities: list[BinarySensorEntity] = []

        if coordinator.enable_host_entities:
            for host_id in coordinator.desired_host_ids():
                for key in host_binary_keys(coordinator.discovery):
                    entity_key = host_entity_key(host_id, key)
                    desired_keys.add(entity_key)
                    if entity_key in entities:
                        continue
                    new_entities.append(
                        BixHostBinarySensor(coordinator, host_id, key, prettify_key(key))
                    )

        if coordinator.enable_job_entities:
            for job_id in coordinator.desired_job_ids():
                for key in job_binary_keys(coordinator.discovery):
                    entity_key = job_entity_key(job_id, key)
                    desired_keys.add(entity_key)
                    if entity_key in entities:
                        continue
                    new_entities.append(
                        BixJobBinarySensor(coordinator, job_id, key, prettify_key(key))
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
        self._label = label
        self._attr_name = f"BIX Job {coordinator.get_job_label(job_id)} {label}"
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

    @property
    def name(self) -> str | None:
        return f"BIX Job {self.coordinator.get_job_label(self._job_id)} {self._label}"


def _entity_key(entity: BinarySensorEntity) -> str:
    host_id = getattr(entity, "_host_id", None)
    key = getattr(entity, "_key", None)
    if isinstance(host_id, str) and isinstance(key, str):
        return host_entity_key(host_id, key)
    job_id = getattr(entity, "_job_id", None)
    if isinstance(job_id, str) and isinstance(key, str):
        return job_entity_key(job_id, key)
    return getattr(entity, "entity_id", repr(entity))
