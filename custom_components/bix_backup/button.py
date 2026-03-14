from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BixBackupCoordinator
from .runtime_model import reconcile_ids


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BixBackupCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: dict[str, ButtonEntity] = {}

    def _sync_dynamic_entities() -> None:
        desired_keys: set[str] = set()
        new_entities: list[ButtonEntity] = []

        if coordinator.enable_action_buttons and coordinator.supports_job_action("run_backup"):
            for job_id in coordinator.desired_job_ids():
                entity_key = f"job:{job_id}:run_backup"
                desired_keys.add(entity_key)
                if entity_key in entities:
                    continue
                new_entities.append(BixRunBackupButton(coordinator, job_id))

        if coordinator.enable_action_buttons and coordinator.enable_alert_entities:
            for alert_id in coordinator.desired_alert_ids():
                if coordinator.supports_alert_action("ack"):
                    entity_key = f"alert:{alert_id}:ack"
                    desired_keys.add(entity_key)
                    if entity_key not in entities:
                        new_entities.append(BixAlertAckButton(coordinator, alert_id))
                if coordinator.supports_alert_action("resolve"):
                    entity_key = f"alert:{alert_id}:resolve"
                    desired_keys.add(entity_key)
                    if entity_key not in entities:
                        new_entities.append(BixAlertResolveButton(coordinator, alert_id))

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


class BixRunBackupButton(CoordinatorEntity[BixBackupCoordinator], ButtonEntity):
    def __init__(self, coordinator: BixBackupCoordinator, job_id: str) -> None:
        super().__init__(coordinator)
        self._job_id = job_id
        self._attr_name = f"BIX Job {coordinator.get_job_label(job_id)} Run Backup"
        self._attr_unique_id = f"bix_job_{job_id}_run_backup"

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        if not self.coordinator.supports_job_action("run_backup"):
            return False
        job = self.coordinator.get_job(self._job_id)
        if job is None:
            return False
        return bool(job.get("can_run_backup"))

    async def async_press(self) -> None:
        try:
            await self.coordinator.async_run_backup(self._job_id)
            self.hass.bus.async_fire(
                "bix_backup_action_succeeded",
                {"action": "run_backup", "job_id": self._job_id},
            )
        except Exception as err:
            self.hass.bus.async_fire(
                "bix_backup_action_failed",
                {"action": "run_backup", "job_id": self._job_id, "error": str(err)},
            )
            raise HomeAssistantError(str(err)) from err

    @property
    def name(self) -> str | None:
        return f"BIX Job {self.coordinator.get_job_label(self._job_id)} Run Backup"

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        job = self.coordinator.get_job(self._job_id)
        if not isinstance(job, dict):
            return None
        attrs = {
            "job_id": self._job_id,
        }
        for key in ("job_name", "host_id"):
            value = str(job.get(key, "")).strip()
            if value:
                attrs[key] = value
        return attrs


class BixAlertAckButton(CoordinatorEntity[BixBackupCoordinator], ButtonEntity):
    def __init__(self, coordinator: BixBackupCoordinator, alert_id: str) -> None:
        super().__init__(coordinator)
        self._alert_id = alert_id
        self._attr_name = f"BIX Alert {alert_id} Acknowledge"
        self._attr_unique_id = f"bix_alert_{alert_id}_ack"

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        if not self.coordinator.supports_alert_action("ack"):
            return False
        alert = self.coordinator.get_alert(self._alert_id)
        if alert is None:
            return False
        return bool(alert.get("can_ack"))

    async def async_press(self) -> None:
        try:
            await self.coordinator.async_ack_alert(self._alert_id)
            self.hass.bus.async_fire(
                "bix_backup_action_succeeded",
                {"action": "ack", "alert_id": self._alert_id},
            )
        except Exception as err:
            self.hass.bus.async_fire(
                "bix_backup_action_failed",
                {"action": "ack", "alert_id": self._alert_id, "error": str(err)},
            )
            raise HomeAssistantError(str(err)) from err

    @property
    def name(self) -> str | None:
        alert = self.coordinator.get_alert(self._alert_id)
        if isinstance(alert, dict):
            job_id = str(alert.get("job_id", "")).strip()
            if job_id:
                return f"BIX Alert {self.coordinator.get_job_label(job_id)} Acknowledge"
        return f"BIX Alert {self._alert_id} Acknowledge"

    @property
    def extra_state_attributes(self) -> dict[str, str | int] | None:
        return _alert_attributes(self.coordinator.get_alert(self._alert_id), "ack")


class BixAlertResolveButton(CoordinatorEntity[BixBackupCoordinator], ButtonEntity):
    def __init__(self, coordinator: BixBackupCoordinator, alert_id: str) -> None:
        super().__init__(coordinator)
        self._alert_id = alert_id
        self._attr_name = f"BIX Alert {alert_id} Resolve"
        self._attr_unique_id = f"bix_alert_{alert_id}_resolve"

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        if not self.coordinator.supports_alert_action("resolve"):
            return False
        alert = self.coordinator.get_alert(self._alert_id)
        if alert is None:
            return False
        return bool(alert.get("can_resolve"))

    async def async_press(self) -> None:
        try:
            await self.coordinator.async_resolve_alert(self._alert_id)
            self.hass.bus.async_fire(
                "bix_backup_action_succeeded",
                {"action": "resolve", "alert_id": self._alert_id},
            )
        except Exception as err:
            self.hass.bus.async_fire(
                "bix_backup_action_failed",
                {"action": "resolve", "alert_id": self._alert_id, "error": str(err)},
            )
            raise HomeAssistantError(str(err)) from err

    @property
    def name(self) -> str | None:
        alert = self.coordinator.get_alert(self._alert_id)
        if isinstance(alert, dict):
            job_id = str(alert.get("job_id", "")).strip()
            if job_id:
                return f"BIX Alert {self.coordinator.get_job_label(job_id)} Resolve"
        return f"BIX Alert {self._alert_id} Resolve"

    @property
    def extra_state_attributes(self) -> dict[str, str | int] | None:
        return _alert_attributes(self.coordinator.get_alert(self._alert_id), "resolve")


def _alert_attributes(alert: dict[str, object] | None, action: str) -> dict[str, str | int] | None:
    if not isinstance(alert, dict):
        return None

    attrs: dict[str, str | int] = {
        "alert_id": str(alert.get("id", "")).strip(),
        "action": action,
    }
    for key in ("job_id", "job_name", "type", "severity", "message", "first_seen_at", "last_seen_at", "last_execution_id"):
        value = str(alert.get(key, "")).strip()
        if value:
            attrs[key] = value
    count = alert.get("count")
    if isinstance(count, int):
        attrs["count"] = count
    return attrs


def _entity_key(entity: ButtonEntity) -> str:
    unique_id = getattr(entity, "unique_id", None)
    if isinstance(unique_id, str) and unique_id:
        if unique_id.startswith("bix_job_") and unique_id.endswith("_run_backup"):
            job_id = unique_id[len("bix_job_") : -len("_run_backup")]
            return f"job:{job_id}:run_backup"
        if unique_id.startswith("bix_alert_") and unique_id.endswith("_ack"):
            alert_id = unique_id[len("bix_alert_") : -len("_ack")]
            return f"alert:{alert_id}:ack"
        if unique_id.startswith("bix_alert_") and unique_id.endswith("_resolve"):
            alert_id = unique_id[len("bix_alert_") : -len("_resolve")]
            return f"alert:{alert_id}:resolve"
    return getattr(entity, "entity_id", repr(entity))
