from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "bix_backup"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

CONF_BASE_URL = "base_url"
CONF_TOKEN = "token"

OPT_POLL_FALLBACK_SECONDS = "poll_fallback_seconds"
OPT_DRIFT_POLL_SECONDS = "drift_poll_seconds"
OPT_ENABLE_HOST_ENTITIES = "enable_host_entities"
OPT_ENABLE_JOB_ENTITIES = "enable_job_entities"
OPT_ENABLE_ALERT_ENTITIES = "enable_alert_entities"
OPT_ENABLE_ACTION_BUTTONS = "enable_action_buttons"

DEFAULT_POLL_FALLBACK_SECONDS = 30
DEFAULT_DRIFT_POLL_SECONDS = 300
DEFAULT_ENABLE_HOST_ENTITIES = True
DEFAULT_ENABLE_JOB_ENTITIES = True
DEFAULT_ENABLE_ALERT_ENTITIES = True
DEFAULT_ENABLE_ACTION_BUTTONS = True

DISCOVERY_PATH = "/api/integrations/home-assistant/discovery"
STATE_PATH = "/api/integrations/home-assistant/state"
ACTIONS_BASE_PATH = "/api/integrations/home-assistant/actions"
WS_PATH = "/ws/ui"

SUPPORTED_WS_EVENTS = {"host", "job", "alerts", "config"}
