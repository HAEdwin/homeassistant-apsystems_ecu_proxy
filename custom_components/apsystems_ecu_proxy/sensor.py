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


async def async_setup_entry(hass: HomeAssistant, config: ConfigType, async_add_entities: AddEntitiesCallback, discovery_info: DiscoveryInfoType | None = None) -> None:
    """Set up the sensor platform."""

    _LOGGER.warning("step 5: async_setup_entry from sensor.py")

# temporary experiment, how to get datadict here? 
    my_sensor_data = {
        "sensor1": {
            "name": "Temperature Sensor",
            "unit_of_measurement": "°C",
            "value": 25.5
        },
        "sensor2": {
            "name": "Humidity Sensor",
            "unit_of_measurement": "%",
            "value": 60
        }
    }
    sensors = []
    for sensor_id, sensor_info in my_sensor_data.items():
        sensors.append(MyCustomSensor(sensor_id, sensor_info))
    async_add_entities(sensors)
    

#=========== This part is to dynamically add sensors ? ====================
class MyCustomSensor(SensorEntity):
    def __init__(self, sensor_id, sensor_info):
        self._sensor_id = sensor_id
        self._name = sensor_info["name"]
        self._unit_of_measurement = sensor_info["unit_of_measurement"]
        self._state = sensor_info["value"]
        
    @property
    def name(self):
        return self._name
    
    @property
    def state(self):
        return self._state
        
    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement

# Something with updating when the datadict changes (every 5 minutes)
    def update(self):
        pass
