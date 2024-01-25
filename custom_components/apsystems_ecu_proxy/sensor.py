from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity import Entity
from homeassistant.const import UnitOfPower
import logging
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    _LOGGER.warning("step 3: async_setup_entry from sensor.py")
    add_entities([MySensor()])


class MySensor(Entity):
    def __init__(self):
        self._state = "Hello, world!"

    @property
    def name(self):
        return "my_sensor"

    @property
    def state(self):
        return self._state

    def update(self):
        self._state = "Hi there!"
