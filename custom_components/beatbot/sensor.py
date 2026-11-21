"""Sensors for the Beatbot custom integration."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

from beatbot_cloud import (
    ERROR_BITS_BY_CATEGORY,
    STATUS_BY_CATEGORY,
    BeatbotDeviceData,
    ProductCategory,
    error_for,
    status_for,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import BeatbotConfigEntry
from .coordinator import BeatbotCoordinator
from .entity import BeatbotEntity

PARALLEL_UPDATES = 0


def _resolve_category(data: BeatbotDeviceData) -> ProductCategory:
    """Resolve a Beatbot product category with a safe pool-bot fallback."""
    try:
        return ProductCategory(data.product_category)
    except ValueError:
        return ProductCategory.POOL_CLEAN_BOT


def _all_status_options() -> list[str]:
    """Return every known status enum value across categories."""
    return list(
        dict.fromkeys(
            status.value
            for mapping in STATUS_BY_CATEGORY.values()
            for status in mapping.values()
        )
    )


def _all_error_options() -> list[str]:
    """Return every known error enum value across categories plus 'none'."""
    return list(
        dict.fromkeys(
            error.value
            for entries in ERROR_BITS_BY_CATEGORY.values()
            for error, _ in entries
        )
    ) + ["none"]


def _status_value(data: BeatbotDeviceData) -> str | None:
    """Return the decoded semantic work status."""
    if data.work_status is None:
        return None
    if status := status_for(_resolve_category(data), data.work_status):
        return status.value
    return None


def _error_value(data: BeatbotDeviceData) -> str | None:
    """Return the first active decoded error, or 'none'."""
    if data.error_code is None:
        return None
    if not data.error_code:
        return "none"
    if error := error_for(_resolve_category(data), data.error_code):
        return error.value
    return None


def _active_errors(data: BeatbotDeviceData) -> list[str]:
    """Decode all active error bits for the device's category."""
    if not data.error_code:
        return []
    category = _resolve_category(data)
    return [
        err.value
        for err, bit in ERROR_BITS_BY_CATEGORY.get(category, ())
        if data.error_code & (1 << bit)
    ]


@dataclass(frozen=True, kw_only=True)
class BeatbotSensorEntityDescription(SensorEntityDescription):
    """Describe a Beatbot sensor entity."""

    value_fn: Callable[[BeatbotDeviceData], StateType]
    attrs_fn: Callable[[BeatbotDeviceData], dict[str, Any]] | None = None
    require_online: bool = False


SENSOR_DESCRIPTIONS: tuple[BeatbotSensorEntityDescription, ...] = (
    BeatbotSensorEntityDescription(
        key="status",
        translation_key="work_status",
        device_class=SensorDeviceClass.ENUM,
        options=_all_status_options(),
        value_fn=_status_value,
        attrs_fn=lambda d: {
            "raw_work_status": d.work_status,
            "work_mode_id": d.work_mode,
            "work_mode_label": d.work_mode_options.get(d.work_mode),
        },
    ),
    BeatbotSensorEntityDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery_level,
    ),
    BeatbotSensorEntityDescription(
        key="error",
        translation_key="error",
        device_class=SensorDeviceClass.ENUM,
        options=_all_error_options(),
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_error_value,
        attrs_fn=lambda d: {
            "raw_error_code": d.error_code,
            "active_errors": _active_errors(d),
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BeatbotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Beatbot sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        BeatbotSensor(coordinator, device_id, description)
        for device_id in coordinator.data
        for description in SENSOR_DESCRIPTIONS
    )


class BeatbotSensor(BeatbotEntity, SensorEntity):
    """Represent a Beatbot sensor."""

    entity_description: BeatbotSensorEntityDescription

    def __init__(
        self,
        coordinator: BeatbotCoordinator,
        device_id: str,
        description: BeatbotSensorEntityDescription,
    ) -> None:
        """Initialize a Beatbot sensor."""
        self._require_online = description.require_online
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    @override
    def native_value(self) -> StateType:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.data)

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra diagnostic attributes when defined."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.data)
