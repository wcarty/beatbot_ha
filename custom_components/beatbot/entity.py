"""Shared base entity for the Beatbot custom integration."""

from typing import override

from beatbot_cloud import BeatbotDeviceData

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BeatbotCoordinator


class BeatbotEntity(CoordinatorEntity[BeatbotCoordinator]):
    """Common base entity providing device metadata and availability."""

    _attr_has_entity_name = True
    _require_online: bool = True

    def __init__(self, coordinator: BeatbotCoordinator, device_id: str) -> None:
        """Initialize a Beatbot entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        data = self.data
        version = next((item.version for item in data.versions if item.version), None)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=data.name or data.model or f"Beatbot {device_id[-6:]}",
            manufacturer="Beatbot",
            model=data.model or None,
            model_id=data.product_id or None,
            sw_version=version,
        )

    @property
    @override
    def available(self) -> bool:
        """Return whether the entity is available."""
        base_available = super().available and self._device_id in self.coordinator.data
        if not self._require_online:
            return base_available
        return base_available and self.data.is_online

    @property
    def data(self) -> BeatbotDeviceData:
        """Return the latest data for this device."""
        return self.coordinator.data[self._device_id]
