from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_BASE_URL,
    CONF_TOKEN,
    DEFAULT_DRIFT_POLL_SECONDS,
    DEFAULT_ENABLE_ACTION_BUTTONS,
    DEFAULT_ENABLE_ALERT_ENTITIES,
    DEFAULT_ENABLE_HOST_ENTITIES,
    DEFAULT_ENABLE_JOB_ENTITIES,
    DEFAULT_POLL_FALLBACK_SECONDS,
    DISCOVERY_PATH,
    DOMAIN,
    OPT_DRIFT_POLL_SECONDS,
    OPT_ENABLE_ACTION_BUTTONS,
    OPT_ENABLE_ALERT_ENTITIES,
    OPT_ENABLE_HOST_ENTITIES,
    OPT_ENABLE_JOB_ENTITIES,
    OPT_POLL_FALLBACK_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


def _normalize_base_url(raw: str) -> str:
    return raw.strip().rstrip("/")


async def _validate_connection(
    session: aiohttp.ClientSession,
    base_url: str,
    token: str,
) -> dict[str, Any]:
    url = f"{base_url}{DISCOVERY_PATH}"
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(url, headers=headers, timeout=15) as resp:
        if resp.status == 401:
            raise ValueError("unauthorized")
        if resp.status >= 400:
            raise ValueError(f"http_{resp.status}")
        payload = await resp.json()
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported_schema")
    return payload


class BixBackupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = _normalize_base_url(str(user_input[CONF_BASE_URL]))
            token = str(user_input[CONF_TOKEN]).strip()
            session = async_get_clientsession(self.hass)
            try:
                discovery = await _validate_connection(session, base_url, token)
            except ValueError as err:
                errors["base"] = str(err)
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:  # pragma: no cover - defensive
                _LOGGER.exception("Unexpected BIX config flow failure")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(base_url)
                self._abort_if_unique_id_configured()
                title = f"BIX Backup ({discovery.get('controller', {}).get('id', 'controller')})"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_BASE_URL: base_url,
                        CONF_TOKEN: token,
                    },
                    options={
                        OPT_POLL_FALLBACK_SECONDS: DEFAULT_POLL_FALLBACK_SECONDS,
                        OPT_DRIFT_POLL_SECONDS: DEFAULT_DRIFT_POLL_SECONDS,
                        OPT_ENABLE_HOST_ENTITIES: DEFAULT_ENABLE_HOST_ENTITIES,
                        OPT_ENABLE_JOB_ENTITIES: DEFAULT_ENABLE_JOB_ENTITIES,
                        OPT_ENABLE_ALERT_ENTITIES: DEFAULT_ENABLE_ALERT_ENTITIES,
                        OPT_ENABLE_ACTION_BUTTONS: DEFAULT_ENABLE_ACTION_BUTTONS,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL): str,
                vol.Required(CONF_TOKEN): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return BixBackupOptionsFlow(config_entry)


class BixBackupOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: Mapping[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=dict(user_input))

        options = self._config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    OPT_POLL_FALLBACK_SECONDS,
                    default=options.get(OPT_POLL_FALLBACK_SECONDS, DEFAULT_POLL_FALLBACK_SECONDS),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
                vol.Required(
                    OPT_DRIFT_POLL_SECONDS,
                    default=options.get(OPT_DRIFT_POLL_SECONDS, DEFAULT_DRIFT_POLL_SECONDS),
                ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
                vol.Required(
                    OPT_ENABLE_HOST_ENTITIES,
                    default=options.get(OPT_ENABLE_HOST_ENTITIES, DEFAULT_ENABLE_HOST_ENTITIES),
                ): bool,
                vol.Required(
                    OPT_ENABLE_JOB_ENTITIES,
                    default=options.get(OPT_ENABLE_JOB_ENTITIES, DEFAULT_ENABLE_JOB_ENTITIES),
                ): bool,
                vol.Required(
                    OPT_ENABLE_ALERT_ENTITIES,
                    default=options.get(OPT_ENABLE_ALERT_ENTITIES, DEFAULT_ENABLE_ALERT_ENTITIES),
                ): bool,
                vol.Required(
                    OPT_ENABLE_ACTION_BUTTONS,
                    default=options.get(OPT_ENABLE_ACTION_BUTTONS, DEFAULT_ENABLE_ACTION_BUTTONS),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
