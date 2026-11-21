"""Constants for the Beatbot custom integration."""

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "beatbot"

PLATFORMS: Final[list[Platform]] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.VACUUM,
]

NETWORK_REFRESH_INTERVAL: Final = 10 * 60

INTERFACE_VACUUM_START: Final = "vacuum.start"
INTERFACE_VACUUM_PAUSE: Final = "vacuum.pause"
INTERFACE_VACUUM_STOP: Final = "vacuum.stop"
INTERFACE_VACUUM_RETURN: Final = "vacuum.return_to_base"
