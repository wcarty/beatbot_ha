"""Vacuum entity for Beatbot robotic pool cleaners."""

from typing import Any, override

from beatbot_cloud import DeviceStatus, ProductCategory, status_for

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeatbotConfigEntry
from .const import (
    INTERFACE_VACUUM_PAUSE,
    INTERFACE_VACUUM_RETURN,
    INTERFACE_VACUUM_START,
    INTERFACE_VACUUM_STOP,
)
from .coordinator import BeatbotCoordinator
from .entity import BeatbotEntity

PARALLEL_UPDATES = 0

_STATUS_TO_ACTIVITY: dict[DeviceStatus, VacuumActivity] = {
    DeviceStatus.CLEANING: VacuumActivity.CLEANING,
    DeviceStatus.DIVING: VacuumActivity.CLEANING,
    DeviceStatus.EMERGE: VacuumActivity.CLEANING,
    DeviceStatus.REMOTE_CONTROL: VacuumActivity.CLEANING,
    DeviceStatus.SELF_CLEANING: VacuumActivity.CLEANING,
    DeviceStatus.CHASE_LIGHT: VacuumActivity.CLEANING,
    DeviceStatus.PAUSED: VacuumActivity.PAUSED,
    DeviceStatus.RETURN_TRIP: VacuumActivity.RETURNING,
    DeviceStatus.GOTO_CHARGE: VacuumActivity.RETURNING,
    DeviceStatus.AUTO_DOCK: VacuumActivity.RETURNING,
    DeviceStatus.CHARGING: VacuumActivity.DOCKED,
    DeviceStatus.CHARGE_DONE: VacuumActivity.DOCKED,
    DeviceStatus.DOCK: VacuumActivity.DOCKED,
    DeviceStatus.DOCK_DONE: VacuumActivity.DOCKED,
    DeviceStatus.REPLENISH_ENERGY: VacuumActivity.DOCKED,
    DeviceStatus.STANDBY: VacuumActivity.IDLE,
    DeviceStatus.SLEEP: VacuumActivity.IDLE,
    DeviceStatus.CLEAN_DONE: VacuumActivity.IDLE,
    DeviceStatus.CLEAN_WAIT: VacuumActivity.IDLE,
    DeviceStatus.FINISH_CONNECT: VacuumActivity.IDLE,
    DeviceStatus.WIFI_CONNECT: VacuumActivity.IDLE,
    DeviceStatus.UNCHECK: VacuumActivity.IDLE,
    DeviceStatus.SELF_CHECKING: VacuumActivity.IDLE,
    DeviceStatus.CHECK_DOWN: VacuumActivity.IDLE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BeatbotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Beatbot pool cleaner vacuum entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        BeatbotPoolCleanerVacuum(coordinator, device_id)
        for device_id, device in coordinator.data.items()
        if device.product_category in (ProductCategory.POOL_CLEAN_BOT, "")
    )


class BeatbotPoolCleanerVacuum(BeatbotEntity, StateVacuumEntity):
    """Represent a Beatbot robotic pool cleaner."""

    _attr_name = None
    _attr_icon = "mdi:robot-vacuum"
    _require_online = False

    def __init__(self, coordinator: BeatbotCoordinator, device_id: str) -> None:
        """Initialize the pool cleaner entity."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_vacuum"

    def _supports_action(self, interface_info: str) -> bool:
        """Return True when the device advertises a controllable capability."""
        cap = self.data.capabilities.get(interface_info)
        return cap is not None and not cap.non_controllable

    @property
    @override
    def supported_features(self) -> VacuumEntityFeature:
        """Compute supported vacuum features from Beatbot discovery capabilities."""
        features = VacuumEntityFeature.STATE
        if self._supports_action(INTERFACE_VACUUM_START):
            features |= VacuumEntityFeature.START
        if self._supports_action(INTERFACE_VACUUM_PAUSE):
            features |= VacuumEntityFeature.PAUSE
        if self._supports_action(INTERFACE_VACUUM_STOP):
            features |= VacuumEntityFeature.STOP
        if self._supports_action(INTERFACE_VACUUM_RETURN):
            features |= VacuumEntityFeature.RETURN_HOME
        return features

    @property
    @override
    def activity(self) -> VacuumActivity | None:
        """Return the current activity of the pool cleaner."""
        if self.data.error_code:
            return VacuumActivity.ERROR
        if self.data.work_status is None:
            return None
        try:
            category = ProductCategory(self.data.product_category)
        except ValueError:
            category = ProductCategory.POOL_CLEAN_BOT
        decoded = status_for(category, self.data.work_status)
        if decoded is None:
            return None
        return _STATUS_TO_ACTIVITY.get(decoded, VacuumActivity.IDLE)

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose raw Beatbot metadata and advertised capabilities."""
        return {
            "is_online": self.data.is_online,
            "work_mode": self.data.work_mode_options.get(self.data.work_mode),
            "work_mode_id": self.data.work_mode,
            "raw_work_status": self.data.work_status,
            "raw_error_code": self.data.error_code,
            "capabilities": sorted(self.data.capabilities),
        }

    @override
    async def async_start(self) -> None:
        """Start or resume cleaning."""
        await self.coordinator.async_send_action(
            self._device_id, INTERFACE_VACUUM_START
        )

    @override
    async def async_pause(self) -> None:
        """Pause the current cleaning cycle."""
        await self.coordinator.async_send_action(
            self._device_id, INTERFACE_VACUUM_PAUSE
        )

    @override
    async def async_stop(self, **kwargs: Any) -> None:
        """Stop the current cleaning cycle."""
        await self.coordinator.async_send_action(
            self._device_id, INTERFACE_VACUUM_STOP
        )

    @override
    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Send the robot back to the waterline / charging base."""
        await self.coordinator.async_send_action(
            self._device_id, INTERFACE_VACUUM_RETURN
        )
