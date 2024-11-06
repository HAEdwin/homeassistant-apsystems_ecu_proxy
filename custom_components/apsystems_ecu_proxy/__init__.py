"""Initialise Module for ECU Proxy."""

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.network import async_get_source_ip
from homeassistant.components.persistent_notification import async_create
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_utc_time_change
from homeassistant.util.dt import as_local

from .api import MySocketAPI
from .const import (
    ATTR_INVERTERS,
    ATTR_TIMESTAMP,
    ATTR_VALUE_IF_NO_UPDATE,
    DOMAIN,
    SOCKET_PORTS,
)
from .helpers import slugify
from .sensor import ECU_SENSORS, INVERTER_CHANNEL_SENSORS, INVERTER_SENSORS, SensorData

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


class APsystemsECUProxyInvalidData(Exception):
    """Class provides passforward for error messages."""


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Get server params and start Proxy."""

    hass.data.setdefault(DOMAIN, {})
    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    api_handler = APIManager(hass, config_entry)
    await api_handler.setup_socket_servers()

    hass.data[DOMAIN][config_entry.entry_id] = {"api_handler": api_handler}

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # Stop socket servers.
    api_handler: APIManager = hass.data[DOMAIN][config_entry.entry_id]["api_handler"]
    await api_handler.async_shutdown()

    # Unload platforms.
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    # Remove the config entry from the hass data object.
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
        _LOGGER.debug("%s unloaded config id - %s", DOMAIN, config_entry.entry_id)

    # Return that unloading was successful.
    return unload_ok


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update being triggered by config entry options updates."""
    _LOGGER.debug("Configuration updated: %s", config_entry.options)

    # Fetch the new 'no_update_timeout' value from the config entry options.
    no_update_timeout = int(config_entry.options.get('no_update_timeout'))

    # Update the APIManager instance with the new value for 'no_update_timeout'.
    api_handler: APIManager = hass.data[DOMAIN][config_entry.entry_id]["api_handler"]
    api_handler.update_no_update_timeout(no_update_timeout)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove individual devices from the integration (ok)."""
    if device_entry is not None:
        # Notify the user that the device has been removed
        async_create(
            hass,
            f"The following device was removed from the system: {device_entry}",
            title="Device removal",
        )
        return True
    return False


class APIManager:
    """Class to manage api."""

    socket_servers: list[MySocketAPI] = []
    migration_required: bool = False

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.hass = hass
        #self.config_entry = config_entry
        
        # Get configuration. If initial data else options.
        self.no_update_timeout = int(
            config_entry.options.get('no_update_timeout', 
            config_entry.data.get('no_update_timeout'))
        )

        # Add listener for midnight reset.
        self.midnight_tracker_unregister = async_track_utc_time_change(
            hass, self.midnight_reset, "0", "0", "0", local=True
        )
        # Add listener for 0 or None if no update.
        self.no_update_timer_unregister = None

    def update_no_update_timeout(self, new_timeout: int):
        """Update the no_update_timeout value."""
        _LOGGER.debug("Updating no_update_timeout to %d", new_timeout)
        self.no_update_timeout = new_timeout

    async def midnight_reset(self, *args):
        """Send dispatcher message to all listeners to reset."""
        _LOGGER.debug("midnight reset")

        attribute_values = {}
        attribute_values[ATTR_TIMESTAMP] = as_local(datetime.now())
        self._request_sensor_to_update(
            f"{DOMAIN}_midnight_reset",
            SensorData(data=0, attributes=attribute_values),
        )

    async def setup_socket_servers(self) -> None:
        """Initialise socket server."""
        host = await async_get_source_ip(self.hass)

        for port in SOCKET_PORTS:
            _LOGGER.debug("Creating server for port %s", port)
            server = MySocketAPI(host, port, self.async_update_callback)
            await server.start()
            self.socket_servers.append(server)

    async def async_shutdown(self) -> None:
        """Run shutdown clean up."""
        for socket_server in self.socket_servers:
            await socket_server.stop()
        self.socket_servers.clear()

        await self.midnight_tracker_unregister()
        if self.no_update_timer_unregister is not None:
            self.no_update_timer_unregister()

    def get_device(self, identifiers):
        """Get device from device registry."""
        device_registry = dr.async_get(self.hass)
        return device_registry.async_get_device(identifiers)

    def async_update_callback(self, data: dict[str, Any]):
        """Dispatcher version of update callback."""

        # Cancel no update timer as we have an update.
        if self.no_update_timer_unregister:
            _LOGGER.debug("Cancel 'No update' timer")
            self.no_update_timer_unregister()
            self.no_update_timer_unregister = None

        ecu_id = data.get("ecu-id")

        # Check if ECU is registered in devices
        if not self.get_device({(DOMAIN, f"ecu_{ecu_id}")}):
            _LOGGER.debug("Found new ECU: %s", ecu_id)
            # Send signal to sensor listener to add new ECU
            async_dispatcher_send(self.hass, f"{DOMAIN}_ecu_register", data)
        else:
            _LOGGER.debug("Update for ECU: %s", ecu_id)
            # Request sensors to update
            for sensor in ECU_SENSORS:
                # Added for summation sensors to get initial attribute values
                attribute_values = {}
                if sensor.summation_entity:
                    attribute_values[ATTR_TIMESTAMP] = data.get(ATTR_TIMESTAMP)
                # Added to support no update value changes
                if sensor.value_if_no_update != -1:
                    attribute_values[ATTR_VALUE_IF_NO_UPDATE] = (
                        sensor.value_if_no_update
                    )
                self._request_sensor_to_update(
                    f"{DOMAIN}_{ecu_id}_{slugify(sensor.name)}",
                    SensorData(
                        data=data.get(sensor.parameter), attributes=attribute_values
                    ),
                )

        # Check if inverters registered in devices
        for uid, inverter in data.get(ATTR_INVERTERS, {}).items():
            if not self.get_device({(DOMAIN, f"inverter_{uid}")}):
                _LOGGER.debug("Found new Inverter: %s", inverter.get("uid"))

                # Add ecu-id to inverter data so that sensor can use this.
                inverter["ecu-id"] = ecu_id

                # Send signal to sensor listener to add new Inverter
                async_dispatcher_send(
                    self.hass, f"{DOMAIN}_inverter_register", inverter
                )
            else:
                _LOGGER.debug("Update for known inverter: %s", inverter.get("uid"))
                for uid, inverter in data.get(ATTR_INVERTERS).items():
                    for inverter_sensor in INVERTER_SENSORS:
                        # Added for summation sensors to get initial attribute values
                        attribute_values = {}
                        if sensor.summation_entity:
                            attribute_values[ATTR_TIMESTAMP] = data.get(ATTR_TIMESTAMP)
                        # Added to support no update value changes
                        if inverter_sensor.value_if_no_update != -1:
                            attribute_values[ATTR_VALUE_IF_NO_UPDATE] = (
                                inverter_sensor.value_if_no_update
                            )
                        self._request_sensor_to_update(
                            f"{DOMAIN}_{ecu_id}_{uid}_{slugify(inverter_sensor.name)}",
                            SensorData(
                                data=inverter.get(inverter_sensor.parameter),
                                attributes=attribute_values,
                            ),
                        )

                    for channel in range(inverter.get("channel_qty", 0)):
                        for inverter_channel_sensor in INVERTER_CHANNEL_SENSORS:
                            try:
                                # Added for summation sensors to get initial attribute values
                                attribute_values = {}
                                if inverter_channel_sensor.summation_entity:
                                    attribute_values[ATTR_TIMESTAMP] = data.get(
                                        ATTR_TIMESTAMP
                                    )
                                # Added to support no update value changes
                                if inverter_channel_sensor.value_if_no_update != -1:
                                    attribute_values[ATTR_VALUE_IF_NO_UPDATE] = (
                                        inverter_channel_sensor.value_if_no_update
                                    )
                                self._request_sensor_to_update(
                                    f"{DOMAIN}_{ecu_id}_{uid}_{slugify(inverter_channel_sensor.name)}_{channel + 1}",
                                    SensorData(
                                        data=inverter.get(
                                            inverter_channel_sensor.parameter
                                        )[channel],
                                        attributes=attribute_values,
                                    ),
                                )
                            except (ValueError, IndexError):
                                _LOGGER.warning("There was a value or index error")
                                continue

        # Start the no update timer with the updated value.
        self.no_update_timer_unregister = async_call_later(
            self.hass, timedelta(seconds=self.no_update_timeout), self.fire_no_update
        )

    def _request_sensor_to_update(self, channel_id: str, data: Any):
        """Send a dispatch message to update sensor."""
        _LOGGER.debug(
            "Requesting %s to update with value %s",
            channel_id.replace(f"{DOMAIN}_", ""),
            data,
        )
        async_dispatcher_send(self.hass, channel_id, data)

    async def fire_no_update(self, *args):
        """Update no update sensors."""
        _LOGGER.debug("Firing no update")
        async_dispatcher_send(
            self.hass,
            f"{DOMAIN}_no_update",
        )
