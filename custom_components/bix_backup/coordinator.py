from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ACTIONS_BASE_PATH,
    CONF_BASE_URL,
    CONF_TOKEN,
    DEFAULT_DRIFT_POLL_SECONDS,
    DEFAULT_ENABLE_ACTION_BUTTONS,
    DEFAULT_ENABLE_ALERT_ENTITIES,
    DEFAULT_ENABLE_HOST_ENTITIES,
    DEFAULT_ENABLE_JOB_ENTITIES,
    DEFAULT_POLL_FALLBACK_SECONDS,
    DISCOVERY_PATH,
    OPT_DRIFT_POLL_SECONDS,
    OPT_ENABLE_ACTION_BUTTONS,
    OPT_ENABLE_ALERT_ENTITIES,
    OPT_ENABLE_HOST_ENTITIES,
    OPT_ENABLE_JOB_ENTITIES,
    OPT_POLL_FALLBACK_SECONDS,
    STATE_PATH,
    SUPPORTED_WS_EVENTS,
)
from .ws_client import BixWsClient

_LOGGER = logging.getLogger(__name__)


class BixApiClient:
    def __init__(self, session: aiohttp.ClientSession, base_url: str, token: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._token = token

    @property
    def base_url(self) -> str:
        return self._base_url

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    async def fetch_discovery(self) -> dict[str, Any]:
        async with self._session.get(self._url(DISCOVERY_PATH), headers=self._headers(), timeout=15) as resp:
            if resp.status >= 400:
                raise HomeAssistantError(f"Discovery failed with status {resp.status}")
            payload = await resp.json()
        if payload.get("schema_version") != 1:
            raise HomeAssistantError("Unsupported schema version")
        return payload

    async def fetch_state(self) -> dict[str, Any]:
        async with self._session.get(self._url(STATE_PATH), headers=self._headers(), timeout=15) as resp:
            if resp.status >= 400:
                raise HomeAssistantError(f"State failed with status {resp.status}")
            payload = await resp.json()
        if payload.get("schema_version") != 1:
            raise HomeAssistantError("Unsupported schema version")
        return payload

    async def post_action(self, path: str) -> dict[str, Any]:
        async with self._session.post(self._url(path), headers=self._headers(), timeout=30) as resp:
            payload = await resp.json(content_type=None)
            if resp.status >= 400:
                detail = payload.get("error") if isinstance(payload, dict) else f"status {resp.status}"
                raise HomeAssistantError(f"Action failed: {detail}")
            if not isinstance(payload, dict):
                raise HomeAssistantError("Invalid action payload")
            return payload


class BixBackupCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.session = async_get_clientsession(hass)
        self.api = BixApiClient(
            self.session,
            str(entry.data[CONF_BASE_URL]).strip().rstrip("/"),
            str(entry.data[CONF_TOKEN]).strip(),
        )
        self.discovery: dict[str, Any] = {}
        self.ws_connected = False
        self._ws_client: BixWsClient | None = None

        self.poll_fallback_seconds = int(
            entry.options.get(OPT_POLL_FALLBACK_SECONDS, DEFAULT_POLL_FALLBACK_SECONDS)
        )
        self.drift_poll_seconds = int(entry.options.get(OPT_DRIFT_POLL_SECONDS, DEFAULT_DRIFT_POLL_SECONDS))
        self.enable_host_entities = bool(
            entry.options.get(OPT_ENABLE_HOST_ENTITIES, DEFAULT_ENABLE_HOST_ENTITIES)
        )
        self.enable_job_entities = bool(entry.options.get(OPT_ENABLE_JOB_ENTITIES, DEFAULT_ENABLE_JOB_ENTITIES))
        self.enable_alert_entities = bool(
            entry.options.get(OPT_ENABLE_ALERT_ENTITIES, DEFAULT_ENABLE_ALERT_ENTITIES)
        )
        self.enable_action_buttons = bool(
            entry.options.get(OPT_ENABLE_ACTION_BUTTONS, DEFAULT_ENABLE_ACTION_BUTTONS)
        )

        super().__init__(
            hass,
            _LOGGER,
            name="BIX Backup",
            update_interval=timedelta(seconds=self.poll_fallback_seconds),
        )

    @property
    def actions_capable(self) -> bool:
        capabilities = self.discovery.get("capabilities")
        if not isinstance(capabilities, dict):
            return False
        return bool(capabilities.get("actions_enabled"))

    async def async_initialize(self) -> None:
        self.discovery = await self.api.fetch_discovery()
        ws_url = str(self.discovery.get("transport", {}).get("ws_url", "")).strip()
        if ws_url:
            self._ws_client = BixWsClient(
                self.session,
                ws_url,
                str(self.entry.data[CONF_TOKEN]).strip(),
                self._handle_ws_event,
                self._handle_ws_status,
            )
            self._ws_client.start()

    async def async_shutdown(self) -> None:
        if self._ws_client is not None:
            await self._ws_client.stop()
            self._ws_client = None

    async def _handle_ws_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if event_type not in SUPPORTED_WS_EVENTS:
            return
        _LOGGER.debug("BIX WS event: %s", payload)
        self.hass.async_create_task(self.async_request_refresh())

    async def _handle_ws_status(self, connected: bool) -> None:
        self.ws_connected = connected
        next_interval = self.drift_poll_seconds if connected else self.poll_fallback_seconds
        self.update_interval = timedelta(seconds=next_interval)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.fetch_state()
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    def get_host(self, host_id: str) -> dict[str, Any] | None:
        for host in self.data.get("hosts", []):
            if host.get("id") == host_id:
                return host
        return None

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        for job in self.data.get("jobs", []):
            if job.get("job_id") == job_id:
                return job
        return None

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        for item in self.data.get("alerts", []):
            if item.get("id") == alert_id:
                return item
        return None

    async def async_run_backup(self, job_id: str) -> dict[str, Any]:
        if not self.actions_capable or not self.enable_action_buttons:
            raise HomeAssistantError("BIX actions are disabled")
        path = f"{ACTIONS_BASE_PATH}/jobs/{job_id}/run-backup"
        payload = await self.api.post_action(path)
        await self.async_request_refresh()
        return payload

    async def async_ack_alert(self, alert_id: str) -> dict[str, Any]:
        if not self.actions_capable or not self.enable_action_buttons:
            raise HomeAssistantError("BIX actions are disabled")
        path = f"{ACTIONS_BASE_PATH}/alerts/{alert_id}/ack"
        payload = await self.api.post_action(path)
        await self.async_request_refresh()
        return payload

    async def async_resolve_alert(self, alert_id: str) -> dict[str, Any]:
        if not self.actions_capable or not self.enable_action_buttons:
            raise HomeAssistantError("BIX actions are disabled")
        path = f"{ACTIONS_BASE_PATH}/alerts/{alert_id}/resolve"
        payload = await self.api.post_action(path)
        await self.async_request_refresh()
        return payload
