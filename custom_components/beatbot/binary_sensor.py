"""Binary sensors for the Beatbot custom integration."""

from typing import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
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
    """Set up Beatbot binary sensors."""
    coordinator = entry.runtime_data.coordinator
    entities: list[BinarySensorEntity] = []
    for device_id in coordinator.data:
        entities.append(BeatbotOnlineBinarySensor(coordinator, device_id))
        entities.append(BeatbotProblemBinarySensor(coordinator, device_id))
    async_add_entities(entities)


class BeatbotOnlineBinarySensor(BeatbotEntity, BinarySensorEntity):
    """Report whether the robot is currently connected to Beatbot cloud.

    Pool cleaners naturally drop Wi-Fi while submerged underwater and reconnect
    at the surface or charging dock; keeping this entity available when offline
    makes submerged/docked automations reliable.
    """

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "online"
    _require_online = False

    def __init__(self, coordinator: BeatbotCoordinator, device_id: str) -> None:
        """Initialize the online connectivity binary sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_online"

    @property
    @override
    def is_on(self) -> bool:
        """Return True if the robot is online."""
        return self.data.is_online


class BeatbotProblemBinarySensor(BeatbotEntity, BinarySensorEntity):
    """Report whether the robot has any active error code."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "problem"
    _require_online = False

    def __init__(self, coordinator: BeatbotCoordinator, device_id: str) -> None:
        """Initialize the problem binary sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_problem"

    @property
    @override
    def is_on(self) -> bool:
        """Return True if any error bit is set."""
        return bool(self.data.error_code)
