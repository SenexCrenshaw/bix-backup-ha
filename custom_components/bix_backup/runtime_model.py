from __future__ import annotations

from collections.abc import Iterable
from typing import Any

DEFAULT_SUPPORTED_WS_EVENTS = ("host", "job", "alerts", "config")

HOST_BINARY_FALLBACK = ("connected", "running")
HOST_SENSOR_FALLBACK = ("last_seen",)
JOB_BINARY_FALLBACK = ("enabled", "running")
JOB_SENSOR_FALLBACK = (
    "last_execution_status",
    "last_execution_time",
    "last_success_time",
    "last_failure_time",
    "last_duration_ms",
    "last_backup_total_files",
    "last_backup_total_bytes",
    "last_backup_data_added_bytes",
    "open_alert_count",
)
SUMMARY_BASE_KEYS = ("connected_hosts", "running_jobs", "jobs_failed_24h")
ALERT_SUMMARY_KEY_MAP = {
    "open_total": "open_alerts_total",
    "open_critical": "open_alerts_critical",
    "open_warning": "open_alerts_warning",
    "open_info": "open_alerts_info",
}


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_of_mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _clean_key(value: Any) -> str:
    return str(value).strip()


def _catalog_keys(discovery: dict[str, Any], section: str, entity_type: str) -> tuple[str, ...]:
    catalog = _mapping(_mapping(discovery).get("entity_catalog"))
    items = _list_of_mappings(catalog.get(section))
    keys: list[str] = []
    for item in items:
        if _clean_key(item.get("type")) != entity_type:
            continue
        key = _clean_key(item.get("key"))
        if key:
            keys.append(key)
    return tuple(keys)


def supported_ws_events(discovery: dict[str, Any]) -> tuple[str, ...]:
    transport = _mapping(_mapping(discovery).get("transport"))
    raw = transport.get("supported_events")
    if not isinstance(raw, list):
        return DEFAULT_SUPPORTED_WS_EVENTS
    out = tuple(key for key in (_clean_key(item) for item in raw) if key)
    return out or DEFAULT_SUPPORTED_WS_EVENTS


def discovery_poll_fallback_seconds(discovery: dict[str, Any], fallback: int) -> int:
    transport = _mapping(_mapping(discovery).get("transport"))
    raw = transport.get("poll_fallback_seconds")
    if isinstance(raw, int) and raw > 0:
        return raw
    return fallback


def discovery_job_actions(discovery: dict[str, Any]) -> tuple[str, ...]:
    capabilities = _mapping(_mapping(discovery).get("capabilities"))
    raw = capabilities.get("job_actions")
    if not isinstance(raw, list):
        return ()
    return tuple(key for key in (_clean_key(item) for item in raw) if key)


def discovery_alert_actions(discovery: dict[str, Any]) -> tuple[str, ...]:
    capabilities = _mapping(_mapping(discovery).get("capabilities"))
    raw = capabilities.get("alert_actions")
    if not isinstance(raw, list):
        return ()
    return tuple(key for key in (_clean_key(item) for item in raw) if key)


def actions_enabled(discovery: dict[str, Any]) -> bool:
    capabilities = _mapping(_mapping(discovery).get("capabilities"))
    return bool(capabilities.get("actions_enabled"))


def host_binary_keys(discovery: dict[str, Any]) -> tuple[str, ...]:
    return _catalog_keys(discovery, "host", "binary_sensor") or HOST_BINARY_FALLBACK


def host_sensor_keys(discovery: dict[str, Any]) -> tuple[str, ...]:
    return _catalog_keys(discovery, "host", "sensor") or HOST_SENSOR_FALLBACK


def job_binary_keys(discovery: dict[str, Any]) -> tuple[str, ...]:
    return _catalog_keys(discovery, "job", "binary_sensor") or JOB_BINARY_FALLBACK


def job_sensor_keys(discovery: dict[str, Any]) -> tuple[str, ...]:
    return _catalog_keys(discovery, "job", "sensor") or JOB_SENSOR_FALLBACK


def summary_sensor_keys(discovery: dict[str, Any]) -> tuple[str, ...]:
    mapped = []
    for key in _catalog_keys(discovery, "alert_summary", "sensor"):
        mapped_key = ALERT_SUMMARY_KEY_MAP.get(key)
        if mapped_key:
            mapped.append(mapped_key)
    if not mapped:
        mapped = list(ALERT_SUMMARY_KEY_MAP.values())
    return SUMMARY_BASE_KEYS + tuple(mapped)


def state_hosts(state: dict[str, Any]) -> list[dict[str, Any]]:
    return _list_of_mappings(_mapping(state).get("hosts"))


def state_jobs(state: dict[str, Any]) -> list[dict[str, Any]]:
    return _list_of_mappings(_mapping(state).get("jobs"))


def state_alerts(state: dict[str, Any]) -> list[dict[str, Any]]:
    return _list_of_mappings(_mapping(state).get("alerts"))


def desired_host_ids(state: dict[str, Any]) -> tuple[str, ...]:
    return tuple(host_id for host_id in (_clean_key(item.get("id")) for item in state_hosts(state)) if host_id)


def desired_job_ids(state: dict[str, Any]) -> tuple[str, ...]:
    return tuple(job_id for job_id in (_clean_key(item.get("job_id")) for item in state_jobs(state)) if job_id)


def desired_alert_ids(state: dict[str, Any]) -> tuple[str, ...]:
    return tuple(alert_id for alert_id in (_clean_key(item.get("id")) for item in state_alerts(state)) if alert_id)


def job_name(job_id: str, state: dict[str, Any], discovery: dict[str, Any]) -> str:
    normalized = _clean_key(job_id)
    for job in state_jobs(state):
        if _clean_key(job.get("job_id")) != normalized:
            continue
        name = _clean_key(job.get("job_name"))
        if name:
            return name
    inventory = _mapping(discovery).get("inventory")
    for item in _list_of_mappings(_mapping(inventory).get("jobs")):
        if _clean_key(item.get("job_id")) != normalized:
            continue
        name = _clean_key(item.get("job_name"))
        if name:
            return name
    return normalized


def job_label(job_id: str, state: dict[str, Any], discovery: dict[str, Any]) -> str:
    normalized = _clean_key(job_id)
    name = job_name(normalized, state, discovery)
    for job in state_jobs(state):
        if _clean_key(job.get("job_id")) != normalized:
            continue
        host_id = _clean_key(job.get("host_id"))
        if host_id:
            return f"{name} ({host_id})"
        return name
    inventory = _mapping(discovery).get("inventory")
    for item in _list_of_mappings(_mapping(inventory).get("jobs")):
        if _clean_key(item.get("job_id")) != normalized:
            continue
        host_id = _clean_key(item.get("host_id"))
        if host_id:
            return f"{name} ({host_id})"
        return name
    return name


def reconcile_ids(existing: Iterable[str], desired: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    existing_set = {item for item in existing if _clean_key(item)}
    desired_set = {item for item in desired if _clean_key(item)}
    to_add = tuple(sorted(desired_set - existing_set))
    to_remove = tuple(sorted(existing_set - desired_set))
    return to_add, to_remove


def prettify_key(key: str) -> str:
    return _clean_key(key).replace("_", " ").title()
