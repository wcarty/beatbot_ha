"""Diagnostics support for the Beatbot custom integration."""

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import BeatbotConfigEntry

TO_REDACT = {
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "sub",
    "client_secret",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BeatbotConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a Beatbot config entry (including raw capabilities)."""
    coordinator = entry.runtime_data.coordinator
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "devices": {
            device_id: asdict(device)
            for device_id, device in (coordinator.data or {}).items()
        },
    }
