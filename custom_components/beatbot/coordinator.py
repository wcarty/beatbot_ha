"""Data coordinator for the Beatbot custom integration."""

from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any, override

from beatbot_cloud import (
    BeatbotAuthenticationError,
    BeatbotClient,
    BeatbotConnectionError,
    BeatbotDeviceData,
    BeatbotEvent,
)

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, NETWORK_REFRESH_INTERVAL

if TYPE_CHECKING:
    from . import BeatbotConfigEntry

_LOGGER = logging.getLogger(__name__)


class BeatbotCoordinator(DataUpdateCoordinator[dict[str, BeatbotDeviceData]]):
    """Coordinate Beatbot cloud data, live WebSocket events, and control actions."""

    config_entry: BeatbotConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: BeatbotClient,
        config_entry: BeatbotConfigEntry,
    ) -> None:
        """Initialize the Beatbot coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=NETWORK_REFRESH_INTERVAL),
            config_entry=config_entry,
        )
        self._pending_events: list[BeatbotEvent] | None = None
        self.api = api
        self._reload_scheduled = False

    @override
    async def _async_update_data(self) -> dict[str, BeatbotDeviceData]:
        self._pending_events = []
        try:
            result = await self._async_fetch_data()
            for event in self._pending_events:
                if (device := result.get(event.device_id)) is not None:
                    event.apply_to(device)
            return result
        finally:
            self._pending_events = None

    async def _async_fetch_data(self) -> dict[str, BeatbotDeviceData]:
        """Fetch discovery metadata and batched runtime states from Beatbot cloud."""
        try:
            devices = await self.api.get_devices()
        except BeatbotAuthenticationError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_error",
            ) from err
        except BeatbotConnectionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_error",
                translation_placeholders={"error": str(err)},
            ) from err

        result: dict[str, BeatbotDeviceData] = {d.device_id: d for d in devices}

        try:
            states = await self.api.get_device_states()
        except BeatbotAuthenticationError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_error",
            ) from err
        except BeatbotConnectionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_error",
                translation_placeholders={"error": str(err)},
            ) from err

        _LOGGER.debug(
            "Beatbot state pull completed (deviceCount=%s)",
            len(states),
        )

        previous_data = self.data if isinstance(self.data, dict) else {}
        for device_id, device in result.items():
            if (previous := previous_data.get(device_id)) is not None:
                is_online = device.is_online
                device.copy_runtime_state_from(previous)
                device.is_online = is_online
            if (state := states.get(device_id)) is not None:
                self._apply_state_with_logging(
                    device_id,
                    device,
                    state.get("states"),
                    state.get("is_online"),
                    source="batch",
                )
            else:
                device.is_online = False

        self._reconcile_device_set(result)
        return result

    @callback
    def _reconcile_device_set(self, result: dict[str, BeatbotDeviceData]) -> None:
        """Keep cached offline devices and reload if a new device appears."""
        initial_refresh = not isinstance(self.data, dict)
        previous_data = self.data if isinstance(self.data, dict) else {}
        previous_ids = set(previous_data)
        current_ids = set(result)
        added_ids = set() if initial_refresh else current_ids - previous_ids

        for device_id in previous_ids - current_ids:
            retained = previous_data[device_id]
            retained.is_online = False
            result[device_id] = retained

        if added_ids:
            _LOGGER.debug("Device discovery changed; added=%s", sorted(added_ids))
            self._schedule_entry_reload()

    @callback
    def _schedule_entry_reload(self) -> None:
        """Reload platforms once when new devices are discovered."""
        if self._reload_scheduled:
            return
        self._reload_scheduled = True
        self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)

    @callback
    def async_apply_device_event(self, event: BeatbotEvent) -> None:
        """Overlay a pushed WebSocket state delta without resetting poll cadence."""
        if self._pending_events is not None:
            self._pending_events.append(event)
        device = self.data.get(event.device_id)
        if device is None:
            _LOGGER.debug("Ignoring event for undiscovered device %s", event.device_id)
            return
        if not event.apply_to(device):
            return
        _LOGGER.debug(
            "Applied Beatbot state event (deviceId=%s, type=%s)",
            event.device_id,
            event.event_type,
        )
        self.last_update_success = True
        self.async_update_listeners()

    async def async_send_action(self, device_id: str, interface_info: str) -> None:
        """Send a parameterless control action to a Beatbot device."""
        try:
            await self.api.send_action(device_id, interface_info)
        except BeatbotAuthenticationError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError("Beatbot authentication expired") from err
        except BeatbotConnectionError as err:
            raise HomeAssistantError(
                f"Failed to send action '{interface_info}' to Beatbot: {err}"
            ) from err
        await self.async_request_refresh()

    async def async_set_work_mode(self, device_id: str, label: str) -> None:
        """Set the cleaning work mode of a Beatbot device."""
        try:
            await self.api.set_work_mode(device_id, label)
        except BeatbotAuthenticationError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError("Beatbot authentication expired") from err
        except BeatbotConnectionError as err:
            raise HomeAssistantError(
                f"Failed to set Beatbot work mode '{label}': {err}"
            ) from err
        await self.async_request_refresh()

    async def async_set_switch(
        self, device_id: str, interface_info: str, is_on: bool
    ) -> None:
        """Set a boolean switch capability on a Beatbot device."""
        label = "on" if is_on else "off"
        try:
            await self.api.set_switch(device_id, interface_info, label)
        except BeatbotAuthenticationError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError("Beatbot authentication expired") from err
        except BeatbotConnectionError as err:
            raise HomeAssistantError(
                f"Failed to set Beatbot switch '{interface_info}' to '{label}': {err}"
            ) from err
        await self.async_request_refresh()

    @staticmethod
    def _apply_state_with_logging(
        device_id: str,
        device: BeatbotDeviceData,
        states: dict[str, Any] | None,
        is_online: bool | None,
        *,
        source: str,
    ) -> None:
        """Apply state update to the device model."""
        _LOGGER.debug(
            "Applying Beatbot state update (source=%s, deviceId=%s)",
            source,
            device_id,
        )
        device.apply_state(states, is_online)
