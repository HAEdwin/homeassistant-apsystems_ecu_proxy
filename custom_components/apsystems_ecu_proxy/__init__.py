""" Initialise Module for ECU Proxy """

import logging
import asyncio
import socket
import socketserver
import threading
import traceback
import re
from datetime import timedelta, datetime
from socketserver import BaseRequestHandler
from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
    )
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

class APSystemsECUProxyInvalidData(Exception):
    """ Class provides passforward for error massages """
    #pass (advies Pylint om weg te halen)

ecu_data = {}

# dit deel werkt
class PROXYSERVER(BaseRequestHandler):
    """ Class provides ecu_data dictionary """
    def handle(self):
        self.ecu_id = None
        (myhost, myport) = self.server.server_address
        rec = self.request.recv(1024)
        try:
            _LOGGER.debug(f"From ECU @{myhost}:{myport} - {rec}")
            decrec = rec.decode('utf-8')

            if decrec[0:7] == "APS18AA": # walk through the ECU
                ecu_data["timestamp"] = str(datetime.strptime(decrec[60:74], '%Y%m%d%H%M%S'))
                ecu_data["ecu-id"] = decrec[18:30]
                if ecu_data["ecu-id"][:4] == "2160":
                    ecu_data["model"] = "ECU-R"
                if ecu_data["ecu-id"][:4] == "2162":
                    ecu_data["model"] = "ECU-R pro"
                if ecu_data["ecu-id"][:4] == "2163":
                    ecu_data["model"] = "ECU-B"
                if ecu_data["ecu-id"][:3] == "215":
                    ecu_data["model"] = "ECU-C"
                ecu_data["lifetime_energy"] = int(decrec[42:60]) / 10
                ecu_data["current_power"] = int(decrec[30:42]) / 100
                ecu_data["qty_of_online_inverters"] = int(decrec[74:77])
                inverters = {}
                for m in re.finditer(r'END\d+', decrec): # walk through inverters
                    inv={}
                    inverter_uid = str(decrec[m.start()+3:m.start()+15])
                    inv["uid"] = str(decrec[m.start()+3:m.start()+15])
                    inv["temperature"] = int(decrec[m.start()+25:m.start()+28]) - 100
                    inv["frequency"] = int(decrec[m.start()+20:m.start()+25]) / 10
                    if str(decrec[m.start() + 3:m.start() + 6]) in [
                            '406', '407', '408', '409', '703', '706'
                            ]:
                        inv.update({"model": "YC600/DS3 series", "channel_qty": 2})
                        power = [int(decrec[m.start() + 63:m.start() + 66]),
                            int(decrec[m.start() + 83:m.start() + 86])]
                        voltage = [int(decrec[m.start() + 51:m.start() + 54])
                            / 10, int(decrec[m.start() + 71:m.start() + 74]) / 10]
                        current = [int(decrec[m.start() + 60:m.start() + 63])
                            / 100, int(decrec[m.start() + 80:m.start() + 83]) / 100]
                        inv.update({"power": power, "voltage": voltage, "current": current})
                    else:
                        if str(decrec[m.start() + 3:m.start() + 6]) in ['801', '802', '806']:
                            inv.update({"model": "QS1", "channel_qty": 4})
                        elif str(decrec[m.start() + 3:m.start() + 6]) in [
                                '501', '502', '503', '504'
                                ]:
                            inv.update({"model": "YC1000/QT2", "channel_qty": 4})
                        power = [int(decrec[m.start() + offset:m.start() + offset + 3])
                            for offset in range(63, 127, 20)]
                        voltage = [int(decrec[m.start() + offset:m.start() + offset + 3]) / 10
                            for offset in range(51, 114, 20)]
                        current = [int(decrec[m.start() + offset:m.start() + offset + 3]) / 100
                            for offset in range(60, 123, 20)]
                        inv.update({"power": power, "voltage": voltage, "current": current})
                    inverters[inverter_uid] = inv
                ecu_data["inverters"] = inverters
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("3.67.1.32", myport)) # don't use ecu.apsystemsema.com or it will loop
            sock.sendall(rec)
            response = sock.recv(1024)
            _LOGGER.debug(f"From EMA: {response}")
            sock.close()
            self.request.send(response)

            # When timediff is to large do not update sensors
            timestamp_str = ecu_data.get('timestamp')
            if timestamp_str != None:
                start_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                end_time = datetime.now()
                time_diff_min = (end_time - start_time).total_seconds() / 60
                _LOGGER.warning(f"Returning ecu_data with timediff {time_diff_min:.2f} minutes: {ecu_data}\n")
                if time_diff_min > 10:
                    _LOGGER.warning("Timediff > 10")
                    ecu_data.clear()
            else:
                ecu_data.clear()
                
        except Exception:
            _LOGGER.warning(f"Exception error = {traceback.format_exc()}")

#=============== zelf toegevoegd ===============================================
def my_update():
    """ Get updated data """
    _LOGGER.debug(f"Update: {ecu_data}")
    return ecu_data

#===============================================================================
async def async_start_proxy(config: dict):
    """Setup the listeners and threads."""
    host = config['host']
    try:
        listener_1 = socketserver.TCPServer((host, 8995), PROXYSERVER)
        thread_1 = threading.Thread(target=listener_1.serve_forever)
        listener_2 = socketserver.TCPServer((host, 8996), PROXYSERVER)
        thread_2 = threading.Thread(target=listener_2.serve_forever)
        listener_4 = socketserver.TCPServer((host, 8997), PROXYSERVER)
        thread_4 = threading.Thread(target=listener_4.serve_forever)
        for threads in thread_1, thread_2, thread_4:
            threads.start()
        _LOGGER.warning("Proxy Started...")
        return True
    except OSError as err:
        if err.errno == 98:
            # Ignore 'server address in use' error @ first setup
            pass
        else:
            raise APSystemsECUProxyInvalidData(err)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):

    """ Get server params and start Proxy """
    data_dict = entry.as_dict().get('data', {})
    await async_start_proxy(data_dict)

    # maak een object van PROXYSERVER
    ecu = PROXYSERVER
    async def do_ecu_update():
        while not ecu_data:
            await asyncio.sleep(10)  # Check every 10 second for filled dict
            _LOGGER.debug("Waiting for data...")
        return await hass.async_add_executor_job(my_update)

    coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=do_ecu_update,
            update_interval=timedelta(seconds=10)
    )

    _LOGGER.debug("Waiting for first data...")
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN] = {
        "ecu" : ecu,
        "coordinator" : coordinator
    }

#    _LOGGER.debug("Waiting for first ecu_data...")
#    await coordinator.async_config_entry_first_refresh()

    # Register the ECU and inverter(s)
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"ecu_{coordinator.data.get('ecu-id')}")},
        manufacturer="APSystems",
        suggested_area="Roof",
        name=f"ECU {coordinator.data.get('ecu-id')}",
        model=f"{coordinator.data.get('model')}",
        )

    inverters = coordinator.data.get("inverters", {})
    for uid,inv_data in inverters.items():
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"inverter_{uid}")},
            manufacturer="APSystems",
            suggested_area="Roof",
            name=f"Inverter {uid}",
            model=inv_data.get("model")
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.warning("First data received...")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    return unload_ok

# Enables users to delete a device
async def async_remove_config_entry_device(hass, config, device_entry) -> bool:
    """ Function to remove inividual devices from the integration (ok) """
    if device_entry is not None:
        # Notify the user that the device has been removed
        hass.components.persistent_notification.async_create(
            f"The following device was removed from the system: {device_entry}",
            title="Device Removed",
        )
        return True
