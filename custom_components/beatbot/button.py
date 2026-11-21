"""Button platform for Beatbot controllable actions."""

from typing import override

from beatbot_cloud.const import (
    INTERFACE_CHILD_LOCK,
    INTERFACE_SENSOR_ERROR,
    INTERFACE_VACUUM_BATTERY,
    INTERFACE_VACUUM_STATE,
    INTERFACE_VOICE_DISTURB,
    INTERFACE_WORK_MODE,
)

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeatbotConfigEntry
from .coordinator import BeatbotCoordinator
from .entity import BeatbotEntity

PARALLEL_UPDATES = 0

_NON_BUTTON_INTERFACES = {
    INTERFACE_WORK_MODE,
    INTERFACE_VACUUM_STATE,
    INTERFACE_VACUUM_BATTERY,
    INTERFACE_SENSOR_ERROR,
    INTERFACE_CHILD_LOCK,
    INTERFACE_VOICE_DISTURB,
}

_ACTION_ICONS: dict[str, str] = {
    "vacuum.start": "mdi:play",
    "vacuum.pause": "mdi:pause",
    "vacuum.stop": "mdi:stop",
    "vacuum.return_to_base": "mdi:home-import-outline",
}


def _humanize_interface(interface_info: str) -> str:
    """Turn an interface key like 'vacuum.return_to_base' into 'Return To Base'."""
    suffix = interface_info.split(".", 1)[-1]
    return suffix.replace("_", " ").title()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BeatbotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create buttons dynamically for every controllable Beatbot action capability."""
    coordinator = entry.runtime_data.coordinator
    entities: list[BeatbotActionButton] = []
    for device_id, device in coordinator.data.items():
        for interface_info, cap in sorted(device.capabilities.items()):
            if cap.non_controllable:
                continue
            if interface_info in _NON_BUTTON_INTERFACES:
                continue
            if interface_info.startswith(("sensor.", "select.", "switch.")):
                continue
            entities.append(
                BeatbotActionButton(coordinator, device_id, interface_info)
            )
    async_add_entities(entities)


class BeatbotActionButton(BeatbotEntity, ButtonEntity):
    """Trigger a parameterless Beatbot cloud action."""

    def __init__(
        self,
        coordinator: BeatbotCoordinator,
        device_id: str,
        interface_info: str,
    ) -> None:
        """Initialize an action button."""
        super().__init__(coordinator, device_id)
        self._interface_info = interface_info
        safe_key = interface_info.replace(".", "_")
        self._attr_unique_id = f"{device_id}_action_{safe_key}"
        self._attr_name = _humanize_interface(interface_info)
        if icon := _ACTION_ICONS.get(interface_info):
            self._attr_icon = icon

    @override
    async def async_press(self) -> None:
        """Dispatch the Beatbot cloud action."""
        await self.coordinator.async_send_action(self._device_id, self._interface_info)
