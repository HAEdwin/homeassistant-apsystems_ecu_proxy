import logging
import asyncio
import socket
import socketserver
import threading
from datetime import timedelta
from socketserver import BaseRequestHandler
from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from datetime import datetime
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
    )
import re

from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

class APSystemsECUProxyInvalidData(Exception):
    pass

data = {}

# dit deel werkt
class PROXYSERVER(BaseRequestHandler):
    def handle(self):
        self.ecu_id = None
        (myhost, myport) = self.server.server_address
        rec = self.request.recv(1024)
        try:
            if rec:
                _LOGGER.warning(f"From ECU @{myhost}:{myport} - {rec}")
                # Build data dictionary
                decrec = rec.decode('utf-8')
                # walk through the ECU
                if decrec[0:7] == "APS18AA":
                    #data = {}
                    data["timestamp"] = str(datetime.strptime(decrec[60:74], '%Y%m%d%H%M%S'))
                    data["inverters"] = {}
                    inverters = {}
                    for m in re.finditer(r'END\d+', decrec):
                        inv={}
                        inverter_uid = str(decrec[m.start()+3:m.start()+15])
                        inv["uid"] = str(decrec[m.start()+3:m.start()+15])
                        inv["temperature"] = int(decrec[m.start()+25:m.start()+28]) - 100
                        inv["frequency"] = int(decrec[m.start()+20:m.start()+25]) / 10
                        if str(decrec[m.start()+3:m.start()+6]) in ['406', '407', '408', '409', '703', '706']:
                            inv["model"] = "YC600/DS3 series"
                            inv["channel_qty"] = 2
                            power = []
                            voltage = []
                            current = []
                            power.append(int(decrec[m.start()+63:m.start()+66]))
                            power.append(int(decrec[m.start()+83:m.start()+86]))
                            inv.update({"power": power})
                            voltage.append(int(decrec[m.start()+51:m.start()+54]) / 10)
                            voltage.append(int(decrec[m.start()+71:m.start()+74]) / 10)
                            inv.update({"voltage": voltage})
                            current.append(int(decrec[m.start()+60:m.start()+63]) / 100)
                            current.append(int(decrec[m.start()+80:m.start()+83]) / 100)
                            inv.update({"current": current})
                        else:
                            if str(decrec[m.start()+3:m.start()+6]) in ['801', '802', '806']:
                                inv["model"] = "QS1"
                            if str(decrec[m.start()+3:m.start()+6]) in ['501', '502', '503', '504']:
                                inv["model"] = "YC1000/QT2"
                            inv["channel_qty"] = 4
                            power = []
                            voltage = []
                            current = []
                            power.append(int(decrec[m.start()+63:m.start()+66]))
                            power.append(int(decrec[m.start()+83:m.start()+86]))
                            power.append(int(decrec[m.start()+103:m.start()+106]))
                            power.append(int(decrec[m.start()+123:m.start()+126]))
                            inv.update({"power": power})
                            voltage.append(int(decrec[m.start()+51:m.start()+54]) / 10)
                            voltage.append(int(decrec[m.start()+71:m.start()+74]) / 10)
                            voltage.append(int(decrec[m.start()+91:m.start()+94]) / 10)
                            voltage.append(int(decrec[m.start()+111:m.start()+114]) / 10)
                            inv.update({"voltage": voltage})
                            current.append(int(decrec[m.start()+60:m.start()+63]) / 100)
                            current.append(int(decrec[m.start()+80:m.start()+83]) / 100)
                            current.append(int(decrec[m.start()+100:m.start()+103]) / 100)
                            current.append(int(decrec[m.start()+120:m.start()+123]) / 100)
                            inv.update({"current": current})
                        inverters[inverter_uid] = inv
                    data["inverters"] = inverters
                    data["ecu-id"] = decrec[18:30]
                    self.ecu_id = decrec[18:30]
                    if data["ecu-id"][:4] == "2160":
                        data["model"] = "ECU-R"
                    if data["ecu-id"][:4] == "2162":
                        data["model"] = "ECU-R pro"
                    if data["ecu-id"][:4] == "2163":
                        data["model"] = "ECU-B"
                    if data["ecu-id"][:3] == "215":
                        data["model"] = "ECU-C"
                    self.ecu_id = decrec[18:30]
                    data["lifetime_energy"] = int(decrec[42:60]) / 10
                    data["current_power"] = int(decrec[30:42]) / 100
                    data["qty_of_online_inverters"] = int(decrec[74:77])
                    _LOGGER.warning (f"Data Dictionary = {data}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("3.67.1.32", myport)) # don't use ecu.apsystemsema.com or it will loop
            sock.sendall(rec)
            response = sock.recv(1024)
            _LOGGER.warning(f"Response from EMA: {response}\n")
            sock.close()
            self.request.send(response)
        except Exception as e:
            LOGGER.warning(f"Exception error = {e}")

#=============== zelf toegevoegd ===============================================
def my_update():
    _LOGGER.debug(f"Update: {data}")
    return data
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
#async def async_setup_entry(hass, entry, async_add_entities): laatste AI aanbeveling

    # haal de server parameters op en start de proxy
    data_dict = entry.as_dict().get('data', {})
    await async_start_proxy(data_dict)

    # maak een object van PROXYSERVER
    ecu = PROXYSERVER
    async def do_ecu_update():
        while not data:
            await asyncio.sleep(10)  # Check every 10 second for filled dict
            _LOGGER.debug("Waiting for data...")
        return await hass.async_add_executor_job(my_update)

    coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=do_ecu_update,
            update_interval=timedelta(seconds=60)
    )

    _LOGGER.debug("Waiting for first data...")
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN] = {
        "ecu" : ecu,
        "coordinator" : coordinator
    }

#    Hier wordt de ECU geregistreerd voor de UI (nog debuggen)
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
        model = inv_data.get("model", "Inverter")
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"inverter_{uid}")},
            manufacturer="APSystems",
            suggested_area="Roof",
            name=f"Inverter {uid}",
            model=inv_data.get("model")
        )

#   dit deel komt uit de ECUR integratie  ==
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.warning("First data received...")
    return True
#===========================================

#    for component in PLATFORMS:
#        hass.async_create_task(
#            hass.config_entries.async_forward_entry_setups(entry, component)
#        )
#    _LOGGER.warning("First data received...")
#    return True

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

async def async_remove_config_entry_device(hass, config, device_entry) -> bool:
    if device_entry is not None:
        # Notify the user that the device has been removed
        hass.components.persistent_notification.async_create(
            f"The following device was removed from the system: {device_entry}",
            title="Device Removed",
        )
        return True
    else:
        return False
