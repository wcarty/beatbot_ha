"""Select platform for Beatbot cleaning mode selection."""

from typing import override

from beatbot_cloud.const import INTERFACE_WORK_MODE

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeatbotConfigEntry
from .coordinator import BeatbotCoordinator
from .entity import BeatbotEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BeatbotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Beatbot work-mode select entities for capable devices."""
    coordinator = entry.runtime_data.coordinator
    entities: list[BeatbotWorkModeSelect] = []
    for device_id, device in coordinator.data.items():
        cap = device.capabilities.get(INTERFACE_WORK_MODE)
        if device.work_mode_options and (cap is None or not cap.non_controllable):
            entities.append(BeatbotWorkModeSelect(coordinator, device_id))
    async_add_entities(entities)


class BeatbotWorkModeSelect(BeatbotEntity, SelectEntity):
    """Select the active cleaning mode advertised by the Beatbot robot."""

    _attr_translation_key = "work_mode"
    _attr_icon = "mdi:pool"

    def __init__(self, coordinator: BeatbotCoordinator, device_id: str) -> None:
        """Initialize the work mode select entity."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_work_mode"

    @property
    @override
    def options(self) -> list[str]:
        """Return the available cleaning mode labels."""
        return list(self.data.work_mode_options.values())

    @property
    @override
    def current_option(self) -> str | None:
        """Return the currently selected cleaning mode label."""
        return self.data.work_mode_options.get(self.data.work_mode)

    @override
    async def async_select_option(self, option: str) -> None:
        """Change the robot's cleaning mode."""
        await self.coordinator.async_set_work_mode(self._device_id, option)
