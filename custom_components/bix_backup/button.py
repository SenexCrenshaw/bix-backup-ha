from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
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
    entities: list[ButtonEntity] = []

    if coordinator.enable_action_buttons and coordinator.actions_capable:
        for job in coordinator.data.get("jobs", []):
            job_id = str(job.get("job_id", "")).strip()
            if job_id:
                entities.append(BixRunBackupButton(coordinator, job_id))
        for alert in coordinator.data.get("alerts", []):
            alert_id = str(alert.get("id", "")).strip()
            if not alert_id:
                continue
            entities.append(BixAlertAckButton(coordinator, alert_id))
            entities.append(BixAlertResolveButton(coordinator, alert_id))

    async_add_entities(entities)


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
