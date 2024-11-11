"""Handles sensor entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_SUMMATION_FACTOR,
    ATTR_SUMMATION_PERIOD,
    ATTR_SUMMATION_TYPE,
    ATTR_TIMESTAMP,
    ATTR_VALUE_IF_NO_UPDATE,
    DOMAIN,
    SOLAR_ICON,
    SummationPeriod,
    SummationType,
)
from .helpers import (
    add_local_timezone,
    get_period_start_timestamp,
    has_changed_period,
    slugify,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class SensorData:
    """Class to pass data to sensor."""

    data: Any
    attributes: dict[str, Any] | None = None


@dataclass
class SummationParameters:
    """Class for summation attributes."""

    value: str
    timestamp: str


@dataclass
class APSystemSensorConfig:
    """Class for a sensor config."""

    unique_id: str | None = None
    name: str | None = None
    device_identifier: str | None = None
    initial_value: SensorData | None = None
    display_uom: str | None = None
    display_precision: int | None = None


@dataclass(frozen=True, kw_only=True)
class APSystemSensorDefinition:
    """Class for sensor definition."""

    name: str
    icon: str | None = None
    parameter: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    unit_of_measurement: str | None = None
    entity_category: EntityCategory | None = None
    summation_entity: bool = False
    summation_period: SummationPeriod | None = None
    summation_type: SummationType | None = None
    summation_factor: float = 1
    value_if_no_update: int | str | None = -1


ECU_SENSORS: tuple[APSystemSensorDefinition, ...] = (
    APSystemSensorDefinition(
        name="Current Power",
        icon=SOLAR_ICON,
        parameter="current_power",
        device_class=SensorDeviceClass.POWER,
        unit_of_measurement=UnitOfPower.WATT,
        value_if_no_update=0,
    ),
    APSystemSensorDefinition(
        name="Hourly Energy Production",
        icon=SOLAR_ICON,
        parameter="current_power",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        summation_entity=True,
        summation_period=SummationPeriod.HOURLY,
        summation_type=SummationType.SUM,
        summation_factor=1000,
    ),
    APSystemSensorDefinition(
        name="Daily Energy Production",
        icon=SOLAR_ICON,
        parameter="current_power",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        summation_entity=True,
        summation_period=SummationPeriod.DAILY,
        summation_type=SummationType.SUM,
        summation_factor=1000,
    ),
    APSystemSensorDefinition(
        name="Lifetime Energy Production",
        icon=SOLAR_ICON,
        parameter="current_power",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        summation_entity=True,
        summation_period=SummationPeriod.LIFETIME,
        summation_type=SummationType.SUM,
        summation_factor=1000,
    ),
    APSystemSensorDefinition(
        name="Lifetime Energy",
        icon=SOLAR_ICON,
        parameter="lifetime_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    APSystemSensorDefinition(
        name="Daily Max Power",
        icon=SOLAR_ICON,
        parameter="current_power",
        device_class=SensorDeviceClass.POWER,
        unit_of_measurement=UnitOfPower.WATT,
        summation_entity=True,
        summation_period=SummationPeriod.DAILY,
        summation_type=SummationType.MAX,
    ),
    APSystemSensorDefinition(
        name="Lifetime Max Power",
        icon=SOLAR_ICON,
        parameter="current_power",
        device_class=SensorDeviceClass.POWER,
        unit_of_measurement=UnitOfPower.WATT,
        summation_entity=True,
        summation_period=SummationPeriod.LIFETIME,
        summation_type=SummationType.MAX,
    ),
    APSystemSensorDefinition(
        name="Inverters Online",
        parameter="qty_of_online_inverters",
        value_if_no_update=0,
    ),
    APSystemSensorDefinition(
        name="Last Update",
        parameter="timestamp",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)


INVERTER_SENSORS: tuple[APSystemSensorDefinition, ...] = (
    APSystemSensorDefinition(
        name="Temperature",
        parameter="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_if_no_update=None,
    ),
    APSystemSensorDefinition(
        name="Frequency",
        parameter="frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        unit_of_measurement=UnitOfFrequency.HERTZ,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_if_no_update=0,
    ),
)

INVERTER_CHANNEL_SENSORS: tuple[APSystemSensorDefinition, ...] = (
    APSystemSensorDefinition(
        name="Power",
        parameter="power",
        device_class=SensorDeviceClass.POWER,
        unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_if_no_update=0,
    ),
    APSystemSensorDefinition(
        name="Voltage",
        parameter="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_if_no_update=0,
    ),
    APSystemSensorDefinition(
        name="Current",
        parameter="current",
        device_class=SensorDeviceClass.CURRENT,
        unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_if_no_update=0,
    ),
)


# ===============================================================================
async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
):
    """Initialise sensor platform."""

    def get_device_entry(device_id):
        """Get device entry by device id."""
        try:
            device_registry = dr.async_get(hass)
            devices = device_registry.devices.get_devices_for_config_entry_id(
                config_entry.entry_id
            )
            return [device for device in devices if device.id == device_id][0]
        except IndexError:
            return None

    def restore_sensors():
        """Restore all previously registered sensors."""
        sensors = []

        entity_registry = er.async_get(hass)
        entries = er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )

        for entry in entries:
            if device := get_device_entry(entry.device_id):
                definition = APSystemSensorDefinition(
                    name=entry.original_name,
                    icon=entry.original_icon,
                    device_class=entry.device_class or entry.original_device_class,
                    unit_of_measurement=entry.unit_of_measurement,
                    entity_category=entry.entity_category,
                )

                config = APSystemSensorConfig(
                    unique_id=entry.unique_id,
                    device_identifier=device.identifiers,
                    display_uom=entry.options.get("sensor", {}).get(
                        "unit_of_measurement"
                    ),
                )

                sensors.append(APSystemsSensor(definition, config, config_entry))

        if sensors:
            add_entities(sensors)

    @callback
    def handle_ecu_registration(data: dict[str, Any]):
        """Handle ECU entity creation."""

        # We have found an ECU that is not registered in the device registry
        # So, create all sensors described in ECU_SENSORS

        _LOGGER.debug("Registering new ECU: %s", data)

        ecu_id = data.get("ecu-id")
        device_identifiers = {(DOMAIN, f"ecu_{ecu_id}")}

        # Create device
        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers=device_identifiers,
            manufacturer="APSystems",
            suggested_area="Roof",
            name=f"ECU {ecu_id}",
            model=f"{data.get('model')}",
        )

        sensors = []
        for sensor in ECU_SENSORS:
            # Added for summation sensors to get initial attribute values
            initial_attribute_values = {}
            if sensor.summation_entity:
                initial_attribute_values[ATTR_TIMESTAMP] = data.get(ATTR_TIMESTAMP)
            if sensor.value_if_no_update != -1:
                initial_attribute_values[ATTR_VALUE_IF_NO_UPDATE] = (
                    sensor.value_if_no_update
                )

            config = APSystemSensorConfig(
                unique_id=f"{ecu_id}_{slugify(sensor.name)}",
                device_identifier=device_identifiers,
                initial_value=SensorData(
                    data=data.get(sensor.parameter), attributes=initial_attribute_values
                ),
            )
            sensors.append(APSystemsSensor(sensor, config, config_entry))
        add_entities(sensors)

    @callback
    def handle_inverter_registration(data: dict[str, Any]):
        """Handle inverter entity creation."""

        # We have found an Inverter that is not registered in the device registry
        # So, create all sensors described in INVERTER_SENSORS and
        # INVERTER_CHANNEL_SENSORS

        _LOGGER.debug("Registering New Inverter: %s", data)

        ecu_id = data.get("ecu-id")
        uid = data.get("uid")
        device_identifiers = {(DOMAIN, f"inverter_{uid}")}

        # Create device
        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers=device_identifiers,
            manufacturer="APSystems",
            suggested_area="Roof",
            name=f"Inverter {data.get('uid')}",
            model=f"{data.get('model')}",
        )

        sensors = []
        for sensor in INVERTER_SENSORS:
            initial_attribute_values = {}
            if sensor.summation_entity:
                initial_attribute_values[ATTR_TIMESTAMP] = data.get(ATTR_TIMESTAMP)
            if sensor.value_if_no_update != -1:
                initial_attribute_values[ATTR_VALUE_IF_NO_UPDATE] = (
                    sensor.value_if_no_update
                )
            config = APSystemSensorConfig(
                unique_id=f"{ecu_id}_{uid}_{slugify(sensor.name)}",
                device_identifier=device_identifiers,
                initial_value=SensorData(
                    data=data.get(sensor.parameter), attributes=initial_attribute_values
                ),
            )
            sensors.append(APSystemsSensor(sensor, config, config_entry))

        # Add Inverter channel sensors
        for channel in range(data.get("channel_qty", 0)):
            for sensor in INVERTER_CHANNEL_SENSORS:
                initial_attribute_values = {}
                if sensor.summation_entity:
                    initial_attribute_values[ATTR_TIMESTAMP] = data.get(ATTR_TIMESTAMP)
                if sensor.value_if_no_update != -1:
                    initial_attribute_values[ATTR_VALUE_IF_NO_UPDATE] = (
                        sensor.value_if_no_update
                    )
                config = APSystemSensorConfig(
                    unique_id=f"{ecu_id}_{uid}_{slugify(sensor.name)}_{channel + 1}",
                    device_identifier=device_identifiers,
                    initial_value=SensorData(
                        data=data.get(sensor.parameter)[channel],
                        attributes=initial_attribute_values,
                    ),
                    name=f"{sensor.name} Ch {channel + 1}",
                )
                sensors.append(APSystemsSensor(sensor, config, config_entry))

        add_entities(sensors)

    # Create listener for ecu or inverter registration.
    # Called by update callback in APManager class.
    # Allows dynamic creating of sensors.
    async_dispatcher_connect(
        hass,
        f"{DOMAIN}_ecu_register",
        handle_ecu_registration,
    )
    async_dispatcher_connect(
        hass,
        f"{DOMAIN}_inverter_register",
        handle_inverter_registration,
    )

    # Restore sensors for this config entry that have been registered previously.
    # Shows active sensors at startup even if no message from ECU yet received.
    # Restored sensors have their values from when HA was previously shut down/restarted.
    restore_sensors()


class APSystemsSensor(RestoreSensor, SensorEntity):
    """Base APSystems sensor class."""

    _attr_has_entity_name = True
    _attr_extra_state_attributes = {}

    def __init__(
        self,
        definition: APSystemSensorDefinition,
        config: APSystemSensorConfig,
        config_entry: ConfigEntry,  # Accept ConfigEntry to get dynamic config values
    ) -> None:
        """Initialise sensor."""
        self._definition = definition
        self._config = config
        self.config_entry = config_entry

        self._attr_device_class = definition.device_class
        self._attr_device_info = DeviceInfo(identifiers=self._config.device_identifier)
        self._attr_icon = definition.icon
        self._attr_name = config.name or definition.name
        self._attr_native_unit_of_measurement = definition.unit_of_measurement
        self._attr_state_class = definition.state_class
        self._attr_unique_id = self._config.unique_id

        self.max_stub_interval = int(self.config_entry.data.get("max_stub_interval"))

    @property
    def is_summation_sensor(self) -> bool:
        """Is this a summation sensor."""
        return (
            hasattr(self, "_attr_extra_state_attributes")
            and self._attr_extra_state_attributes.get(ATTR_SUMMATION_PERIOD)
        ) or self._definition.summation_entity

    @property
    def no_update_value(self) -> str | int | None:
        """Is this a reset on no update sensor."""
        return self._attr_extra_state_attributes.get(ATTR_VALUE_IF_NO_UPDATE, -1)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._config.unique_id}",
                self.update_state,
            )
        )
        # Restore state
        if self._config.initial_value:
            self.set_initial_value()
        else:
            await self.restore_state()

        # Dispatcher Listener for midnight reset
        if self.is_summation_sensor:
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass,
                    f"{DOMAIN}_midnight_reset",
                    self.update_state,
                )
            )

        # Dispatcher Listener for 0 or None then no update
        if self.no_update_value != -1:
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass,
                    f"{DOMAIN}_no_update",
                    self.set_no_update_value,
                )
            )

    async def set_no_update_value(self):
        """Set no update value."""
        _LOGGER.debug(
            "Setting no update value of %s on %s", self.no_update_value, self.name
        )
        self._attr_native_value = self.no_update_value
        self.async_write_ha_state()

    async def restore_state(self):
        """Get restored state from store."""
        if (state := await self.async_get_last_state()) is not None:
            # Set unit of measurement in case user has changed this in UI
            self._attr_unit_of_measurement = state.attributes.get(
                ATTR_UNIT_OF_MEASUREMENT
            )
            self._attr_extra_state_attributes = state.attributes

        if (state_data := await self.async_get_last_sensor_data()) is not None:
            # Set our native values
            if state_data.native_unit_of_measurement is not None:
                self._attr_native_unit_of_measurement = (
                    state_data.native_unit_of_measurement
                )
            if state_data.native_value is not None:
                self._attr_native_value = state_data.native_value

            _LOGGER.debug(
                "Restored state for %s of %s with native uom %s and uom %s",
                self.entity_id,
                state_data.native_value,
                state_data.native_unit_of_measurement,
                self._attr_unit_of_measurement,
            )

    def set_initial_value(self):
        """Set initial values on sensor creation."""
        if self._config.initial_value is not None:
            if self._definition.value_if_no_update != -1:
                self.update_attributes(
                    {ATTR_VALUE_IF_NO_UPDATE: self._definition.value_if_no_update}
                )
            if self._definition.summation_entity:
                self.set_summation_entity_attributes()

                if self._definition.summation_type == SummationType.SUM:
                    self._attr_native_value = 0
                else:
                    self._attr_native_value = self._config.initial_value.data

            elif (
                self._definition.device_class == SensorDeviceClass.TIMESTAMP
                and isinstance(self._config.initial_value.data, datetime)
            ):
                # Need to have a timezone for timestamp sensor
                self._attr_native_value = add_local_timezone(
                    self.hass, self._config.initial_value.data
                )
            else:
                self._attr_native_value = self._config.initial_value.data

    def set_summation_entity_attributes(self):
        """Set initial base attribute values."""
        self.update_attributes(
            {
                ATTR_SUMMATION_PERIOD: self._definition.summation_period,
                ATTR_SUMMATION_TYPE: self._definition.summation_type,
                ATTR_SUMMATION_FACTOR: self._definition.summation_factor,
                ATTR_TIMESTAMP: self._config.initial_value.attributes.get(
                    ATTR_TIMESTAMP
                ),
            }
        )

    def update_attributes(self, attributes: dict[str, Any]):
        """Update attribute values."""
        current_attributes = self._attr_extra_state_attributes.copy()
        current_attributes.update(attributes)
        self._attr_extra_state_attributes = current_attributes

    @callback
    def update_state(self, update_data: SensorData):
        """Update sensor value."""
        update_value = update_data.data

        # If summation entity, calculate value
        # This will error reading _attr_extra_state_attributes when sensor first created,
        # so check.
        if self.is_summation_sensor:
            summation_period = self._attr_extra_state_attributes.get(
                ATTR_SUMMATION_PERIOD
            )
            summation_type = self._attr_extra_state_attributes.get(ATTR_SUMMATION_TYPE)
            summation_factor = self._attr_extra_state_attributes.get(
                ATTR_SUMMATION_FACTOR
            )

            current_timestamp = update_data.attributes.get(ATTR_TIMESTAMP)
            last_timestamp = self._attr_extra_state_attributes.get(ATTR_TIMESTAMP)
            # Convert base timestamp attribute from string if needed
            if not isinstance(last_timestamp, datetime):
                last_timestamp = dt_util.parse_datetime(last_timestamp)

            update_value, has_changed = self.summation_calculation(
                summation_period,
                summation_type,
                summation_factor,
                last_timestamp,
                current_timestamp,
                self.native_value,
                update_value,
            )

            # Set timestamp if value changed
            # To only update on min/max summation sensor if changed
            if has_changed:
                self.update_attributes({ATTR_TIMESTAMP: current_timestamp})

        # Update value if no update attribute to allow changes to definition to take effect
        if update_data.attributes.get(ATTR_VALUE_IF_NO_UPDATE, -1) != -1:
            self.update_attributes(
                {
                    ATTR_VALUE_IF_NO_UPDATE: update_data.attributes.get(
                        ATTR_VALUE_IF_NO_UPDATE
                    ),
                }
            )

        # Prevent updating total increasing sensors (ie historical energy sensors)
        # with lower values.
        if (
            self.state_class == SensorStateClass.TOTAL_INCREASING
            and update_value < self.native_value
        ):
            return

        # Timestamp sensor needs a timezone.  As our timestamp data is timezone unaware,
        # give it timezone.
        if self.device_class == SensorDeviceClass.TIMESTAMP and isinstance(
            update_value, datetime
        ):
            update_value = add_local_timezone(self.hass, update_value)

        _LOGGER.debug(
            "Updating sensor: %s with value %s and attributes %s",
            self.entity_id,
            update_value,
            update_data.attributes,
        )
        self._attr_native_value = update_value
        self.async_write_ha_state()

    def summation_calculation(
        self,
        summation_period: SummationPeriod,
        summation_type: SummationType,
        summation_factor: float,
        last_timestamp: datetime,
        current_timestamp: datetime,
        current_value: float,
        value: float,
    ) -> int | float:
        """Return summation value of value over time.

        If change in period, calculates a value over time from start of new period with
        max of MAX_STUB_INTERVAL.
        If no change in period, assumes value persisted since last timestamp.
        """

        _LOGGER.debug(
            "Summation values: Period: %s, Timestamp - current: %s, last: %s, Value - sensor: %s, current: %s",
            summation_period,
            current_timestamp.replace(tzinfo=None),
            last_timestamp.replace(tzinfo=None),
            current_value,
            value,
        )

        # Removing TZ info enables maths on mixed TZ-aware or TZ-naive values used
        interval = (
            current_timestamp.replace(tzinfo=None) - last_timestamp.replace(tzinfo=None)
        ).seconds

        sum_value = None
        has_changed = False

        # Get configuration. If initial data else options.

        _LOGGER.debug("Max stub interval = %s", self.max_stub_interval)

        # Has it crossed calculation period boundry?
        if has_changed_period(summation_period, last_timestamp, current_timestamp):
            # Set to last recorded value if new recording period
            has_changed = True
            if summation_type in [SummationType.MAX, SummationType.MIN]:
                sum_value = value
                _LOGGER.debug(
                    "New summation period - Value: %f",
                    sum_value,
                )
            elif summation_type == SummationType.SUM:
                # Calculate portion of current value to set as start value
                new_period_interval = max(
                    (
                        current_timestamp
                        - get_period_start_timestamp(
                            summation_period, current_timestamp
                        )
                    ).total_seconds(),
                    self.max_stub_interval,
                )
                sum_value = round(
                    int(value * (new_period_interval / 3600)) / summation_factor, 2
                )
                _LOGGER.debug(
                    "New summation period - Period interval(s): %i, Value: %f",
                    new_period_interval,
                    sum_value,
                )
        else:
            sum_value = current_value
            if (
                summation_type == SummationType.MAX
                and value >= current_value
                or summation_type == SummationType.MIN
                and value <= current_value
            ):
                sum_value = value
                has_changed = True
            elif summation_type == SummationType.SUM:
                has_changed = True
                sum_value = round(
                    (current_value + int(value * (interval / 3600)) / summation_factor),
                    2,
                )

            _LOGGER.debug(
                "Same summation period - Period interval(s): %s, Value: %f",
                interval,
                sum_value,
            )

        return sum_value, has_changed
