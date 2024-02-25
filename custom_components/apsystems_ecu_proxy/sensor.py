from __future__ import annotations

from datetime import timedelta, datetime, date
import logging

import async_timeout
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity import Entity, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.core import HomeAssistant

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass
)

from .const import (
    DOMAIN,
    SOLAR_ICON,
    FREQ_ICON,
    DCVOLTAGE_ICON
)
from homeassistant.const import (
    UnitOfPower,
    UnitOfEnergy,
    UnitOfTemperature,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfFrequency
)

_LOGGER = logging.getLogger(__name__)

#===============================================================================
async def async_setup_entry(hass, config, add_entities, discovery_info=None):
    
    ecu = hass.data[DOMAIN].get("ecu")
    coordinator = hass.data[DOMAIN].get("coordinator")
    
    #instance_attributes = [attr for attr in vars(ecu)]
    #_LOGGER.warning(f"attributes:{instance_attributes}")
    
    inverters = coordinator.data.get("inverters", {})
    
    ecu_id = coordinator.data.get("ecu-id")
    #vanaf hier moeten alle gegevens bekend zijn! coordinator.data bevat de volledige datadictionary
    
    
    if not coordinator.data:
        _LOGGER.warning("Tijdelijke dummy data ingezet")
        coordinator.data = {'timestamp': None, 'inverters': {None: {'uid': None, 'temperature': None, 'frequency': None, 'model': None, 'channel_qty': None, 'power': [None, None], 'voltage': [None, None], 'current': [None, None]}}, 'ecu-id': None, 'lifetime_energy': None, 'current_power': None, 'qty_of_online_inverters': None}

    sensors = [
        APSystemsECUSensor(coordinator, ecu, "current_power", 
            label="Current Power",
            unit=UnitOfPower.WATT,
            devclass=SensorDeviceClass.POWER,
            icon=SOLAR_ICON,
            stateclass=SensorStateClass.MEASUREMENT
        ),
#        Onderstaande parameter wordt niet geupload naar EMA
#        APSystemsECUSensor(coordinator, ecu, "today_energy", 
#            label="Today Energy",
#            unit=UnitOfEnergy.KILO_WATT_HOUR,
#            devclass=SensorDeviceClass.ENERGY,
#            icon=SOLAR_ICON,
#            stateclass=SensorStateClass.TOTAL_INCREASING
#        ),
        APSystemsECUSensor(coordinator, ecu, "lifetime_energy", 
            label="Lifetime Energy",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            devclass=SensorDeviceClass.ENERGY,
            icon=SOLAR_ICON,
            stateclass=SensorStateClass.TOTAL_INCREASING
        ),
        APSystemsECUSensor(coordinator, ecu, "qty_of_online_inverters", 
            label="Inverters Online",
            icon=SOLAR_ICON,
            entity_category=EntityCategory.DIAGNOSTIC
        ),
    ]

    
    # als ik onderstaande regel weg haal, dan wordt er geen update meer gedaan en zijn de entities niet aangemaakt (hier komt ie eenmalig)
    #coordinator.data = {'timestamp': '2024-02-15 11:26:49', 'inverters': {'408000111074': {'uid': '408000111074', 'temperature': 16, 'frequency': 50.0, 'model': 'YC600/DS3 series', 'channel_qty': 2, 'power': [29, 29], 'voltage': [34.3, 34.0], 'current': [3.2, 3.38]}, '806000011026': {'uid': '806000011026', 'temperature': 16, 'frequency': 50.0, 'model': 'QS1', 'channel_qty': 4, 'power': [45, 54, 59, 52], 'voltage': [33.7, 33.8, 33.2, 33.2], 'current': [5.73, 3.0, 7.48, 1.17]}}, 'ecu-id': '216000064240', 'lifetime_energy': 2139.1, 'current_power': 268.0, 'qty_of_online_inverters': 2}
    if coordinator.data:
        inverters = coordinator.data.get("inverters", {})
        for uid,inv_data in inverters.items():
            _LOGGER.debug(f"Inverter {uid} {inv_data.get('channel_qty')}")
            if inv_data.get("channel_qty") != None:
                sensors.extend([
                        APSystemsECUInverterSensor(coordinator, ecu, uid, "temperature",
                            label="Temperature",
                            unit=UnitOfTemperature.CELSIUS,
                            devclass=SensorDeviceClass.TEMPERATURE,
                            stateclass=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC
                        ),
                        APSystemsECUInverterSensor(coordinator, ecu, uid, "frequency",
                            label="Frequency",
                            unit=UnitOfFrequency.HERTZ,
                            stateclass=SensorStateClass.MEASUREMENT,
                            devclass=SensorDeviceClass.FREQUENCY,
                            icon=FREQ_ICON,
                            entity_category=EntityCategory.DIAGNOSTIC
                        ),
                ])
                for i in range(0, inv_data.get("channel_qty", 0)):
                    sensors.append(
                        APSystemsECUInverterSensor(coordinator, ecu, uid, f"power", 
                            index=i, label=f"Power Ch {i+1}",
                            unit=UnitOfPower.WATT,
                            devclass=SensorDeviceClass.POWER,
                            icon=SOLAR_ICON,
                            stateclass=SensorStateClass.MEASUREMENT
                        ),
                    ),
                    sensors.append(
                        APSystemsECUInverterSensor(coordinator, ecu, uid, "voltage",
                            index=i, label=f"Voltage Ch {i+1}",
                            unit=UnitOfElectricPotential.VOLT,
                            devclass=SensorDeviceClass.VOLTAGE,
                            icon=DCVOLTAGE_ICON,
                            stateclass=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC
                        ),
                    ),
                    sensors.append(    
                        APSystemsECUInverterSensor(coordinator, ecu, uid, "current",
                            index=i, label=f"Current Ch {i+1}",
                            unit=UnitOfElectricCurrent.AMPERE,
                            devclass=SensorDeviceClass.CURRENT,
                            icon=DCVOLTAGE_ICON,
                            stateclass=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC
                        ),
                    )
                        
        add_entities(sensors)
    
    
    
    
    
#    for uid,inv_data in inverters.items():
#        _LOGGER.debug(f"Inverter {uid} {inv_data.get('channel_qty')}")
#        # https://github.com/ksheumaker/homeassistant-apsystems_ecur/issues/110
#        if inv_data.get("channel_qty") != None:
#            sensors.extend([
#                    APSystemsECUInverterSensor(coordinator, ecu, uid, "temperature",
#                        label="Temperature",
#                        unit=UnitOfTemperature.CELSIUS,
#                        devclass=SensorDeviceClass.TEMPERATURE,
#                        stateclass=SensorStateClass.MEASUREMENT,
#                        entity_category=EntityCategory.DIAGNOSTIC
#                    ),
#                    APSystemsECUInverterSensor(coordinator, ecu, uid, "frequency",
#                        label="Frequency",
#                        unit=UnitOfFrequency.HERTZ,
#                        stateclass=SensorStateClass.MEASUREMENT,
#                        devclass=SensorDeviceClass.FREQUENCY,
#                        icon=FREQ_ICON,
#                        entity_category=EntityCategory.DIAGNOSTIC
#                    ),
#            ])
#            for i in range(0, inv_data.get("channel_qty", 0)):
#                sensors.append(
#                    APSystemsECUInverterSensor(coordinator, ecu, uid, f"power", 
#                        index=i, label=f"Power Ch {i+1}",
#                        unit=UnitOfPower.WATT,
#                        devclass=SensorDeviceClass.POWER,
#                        icon=SOLAR_ICON,
#                        stateclass=SensorStateClass.MEASUREMENT
#                    ),
#                )
#                sensors.append(
#                    APSystemsECUInverterSensor(coordinator, ecu, uid, "current",
#                        index=i, label=f"Current Ch {i+1}",
#                        unit=UnitOfElectricCurrent.AMPERE,
#                        devclass=SensorDeviceClass.CURRENT,
#                        icon=DCVOLTAGE_ICON,
#                        stateclass=SensorStateClass.MEASUREMENT,
#                        entity_category=EntityCategory.DIAGNOSTIC
#                    ),
#                )
#                sensors.append(
#                    APSystemsECUInverterSensor(coordinator, ecu, uid, "voltage",
#                        index=i, label=f"Voltage Ch {i+1}",
#                        unit=UnitOfElectricPotential.VOLT,
#                        devclass=SensorDeviceClass.VOLTAGE,
#                        icon=DCVOLTAGE_ICON,
#                        stateclass=SensorStateClass.MEASUREMENT,
#                        entity_category=EntityCategory.DIAGNOSTIC
#                    ),
#                )
#    add_entities(sensors)

class APSystemsECUInverterSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, ecu, uid, field, index=0, label=None, icon=None, unit=None, devclass=None, stateclass=None, entity_category=None):

        super().__init__(coordinator)

        self.coordinator = coordinator
        self._index = index
        self._uid = uid
        self._ecu = self.coordinator.data.get('ecu-id')
        self._field = field
        self._devclass = devclass
        self._label = label
        if not label:
            self._label = field
        self._icon = icon
        self._unit = unit
        self._stateclass = stateclass
        self._entity_category = entity_category
        self._name = f"Inverter {self._uid} {self._label}"
        self._state = None

    @property
    def unique_id(self):
        field = self._field
        if self._index != None:
            field = f"{field}_{self._index}"
        return f"{self._ecu}_{self._uid}_{field}"

    @property
    def device_class(self):
        return self._devclass

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        _LOGGER.debug(f"State called for {self._field}")
        if self._field == "voltage":
            return self.coordinator.data.get("inverters", {}).get(self._uid, {}).get("voltage", [])[self._index]
        elif self._field == "power":
            return self.coordinator.data.get("inverters", {}).get(self._uid, {}).get("power", [])[self._index]
        elif self._field == "current":
            return self.coordinator.data.get("inverters", {}).get(self._uid, {}).get("current", [])[self._index]
        else:
            return self.coordinator.data.get("inverters", {}).get(self._uid, {}).get(self._field)

    @property
    def icon(self):
        return self._icon

    @property
    def unit_of_measurement(self):
        return self._unit


    @property
    def extra_state_attributes(self):
        attrs = {
            "ecu_id" : f"{self._ecu}",
            "last_update" : f"{self.coordinator.data.get('timestamp')}",
        }
        return attrs

    @property
    def state_class(self):
        _LOGGER.debug(f"State class {self._stateclass} - {self._field}")
        return self._stateclass

    @property
    def device_info(self):
        parent = f"inverter_{self._uid}"
        return {
            "identifiers": {
                (DOMAIN, parent),
            }
        }

    @property
    def entity_category(self):
        return self._entity_category

class APSystemsECUSensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator, ecu, field, label=None, icon=None, unit=None, devclass=None, stateclass=None, entity_category=None):

        super().__init__(coordinator)

        self.coordinator = coordinator
# Hier worden de basis gegevens van de integratie (device info weergegeven)
        self._ecu = self.coordinator.data.get('ecu-id')
        self._field = field
        self._label = label
        if not label:
            self._label = field
        self._icon = icon
        self._unit = unit
        self._devclass = devclass
        self._stateclass = stateclass
        self._entity_category = entity_category
        self._name = f"ECU {self._label}"
        self._state = None

    @property
    def unique_id(self):
        return f"{self._ecu}_{self._field}"

    @property
    def name(self):
        return self._name

    @property
    def device_class(self):
        return self._devclass

    @property
    def state(self):
        _LOGGER.debug(f"State called for {self._field}")
        return self.coordinator.data.get(self._field)

    @property
    def icon(self):
        return self._icon

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def extra_state_attributes(self):
        attrs = {
            "ecu_id" : f"{self._ecu}",
            "last_update" : f"{self.coordinator.data.get('timestamp')}",
        }
        return attrs

    @property
    def state_class(self):
        _LOGGER.debug(f"State class {self._stateclass} - {self._field}")
        return self._stateclass

    @property
    def device_info(self):
        parent = f"ecu_{self._ecu}"
        return {
            "identifiers": {
                (DOMAIN, parent),
            }
        }

    @property
    def entity_category(self):
        return self._entity_category
