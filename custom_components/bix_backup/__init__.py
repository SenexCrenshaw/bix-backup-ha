from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import async_register_built_in_panel, async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import BixBackupCoordinator

PANEL_URL_PATH = "bix-backup"
PANEL_TITLE = "BIX Backup"
PANEL_ICON = "mdi:backup-restore"
PANEL_ELEMENT = "bix-backup-panel"
PANEL_STATIC_URL = "/bix_backup_panel/bix-backup-panel.js"


async def _async_register_panel(hass: HomeAssistant) -> None:
    panel_file = Path(__file__).resolve().parent / "frontend" / "bix-backup-panel.js"
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get("_panel_static_registered"):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(PANEL_STATIC_URL, str(panel_file), cache_headers=False)]
        )
        domain_data["_panel_static_registered"] = True
    async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL_PATH,
        config={
            "_panel_custom": {
                "name": PANEL_ELEMENT,
                "module_url": PANEL_STATIC_URL,
                "embed_iframe": False,
                "trust_external": True,
            },
            "title": PANEL_TITLE,
        },
        require_admin=False,
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = BixBackupCoordinator(hass, entry)
    await coordinator.async_initialize()
    await coordinator.async_config_entry_first_refresh()

    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data[entry.entry_id] = coordinator
    if not domain_data.get("_panel_registered"):
        await _async_register_panel(hass)
        domain_data["_panel_registered"] = True
        domain_data["_panel_entry_count"] = 0
    domain_data["_panel_entry_count"] = int(domain_data.get("_panel_entry_count", 0)) + 1

    async def _async_reload(updated_hass: HomeAssistant, updated_entry: ConfigEntry) -> None:
        await updated_hass.config_entries.async_reload(updated_entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: BixBackupCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_shutdown()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        domain_data = hass.data[DOMAIN]
        domain_data.pop(entry.entry_id)
        remaining = max(int(domain_data.get("_panel_entry_count", 1)) - 1, 0)
        domain_data["_panel_entry_count"] = remaining
        if remaining == 0 and domain_data.get("_panel_registered"):
            async_remove_panel(hass, PANEL_URL_PATH)
            domain_data["_panel_registered"] = False
    return unloaded
