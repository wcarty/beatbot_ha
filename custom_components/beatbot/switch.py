"""Switch platform for Beatbot device settings (child lock, voice DND)."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

from beatbot_cloud import BeatbotDeviceData
from beatbot_cloud.const import INTERFACE_CHILD_LOCK, INTERFACE_VOICE_DISTURB

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeatbotConfigEntry
from .coordinator import BeatbotCoordinator
from .entity import BeatbotEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class BeatbotSwitchEntityDescription(SwitchEntityDescription):
    """Describe a Beatbot switch capability."""

    interface_info: str
    value_fn: Callable[[BeatbotDeviceData], bool]


SWITCH_DESCRIPTIONS: tuple[BeatbotSwitchEntityDescription, ...] = (
    BeatbotSwitchEntityDescription(
        key="child_lock",
        translation_key="child_lock",
        icon="mdi:lock",
        entity_category=EntityCategory.CONFIG,
        interface_info=INTERFACE_CHILD_LOCK,
        value_fn=lambda data: data.child_lock,
    ),
    BeatbotSwitchEntityDescription(
        key="voice_disturb",
        translation_key="voice_disturb",
        icon="mdi:volume-off",
        entity_category=EntityCategory.CONFIG,
        interface_info=INTERFACE_VOICE_DISTURB,
        value_fn=lambda data: data.voice_disturb,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BeatbotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Beatbot switches for capabilities advertised by each device."""
    coordinator = entry.runtime_data.coordinator
    entities: list[BeatbotSwitch] = []
    for device_id, device in coordinator.data.items():
        for description in SWITCH_DESCRIPTIONS:
            cap = device.capabilities.get(description.interface_info)
            if cap is not None and not cap.non_controllable:
                entities.append(BeatbotSwitch(coordinator, device_id, description))
    async_add_entities(entities)


class BeatbotSwitch(BeatbotEntity, SwitchEntity):
    """Represent a controllable Beatbot switch."""

    entity_description: BeatbotSwitchEntityDescription

    def __init__(
        self,
        coordinator: BeatbotCoordinator,
        device_id: str,
        description: BeatbotSwitchEntityDescription,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    @override
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self.entity_description.value_fn(self.data)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.async_set_switch(
            self._device_id, self.entity_description.interface_info, True
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.async_set_switch(
            self._device_id, self.entity_description.interface_info, False
        )
