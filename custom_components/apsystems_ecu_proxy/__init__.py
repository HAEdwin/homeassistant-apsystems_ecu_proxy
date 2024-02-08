import logging
import asyncio
import socket
import socketserver
import threading
from socketserver import BaseRequestHandler
from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from datetime import datetime
import re

from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

datadict = {}
datadict["ECU"] = {}
datadict["Inverters"] = []

class APSystemsECUProxyInvalidData(Exception):
    pass

class PROXYSERVER(BaseRequestHandler):
    def handle(self):
#        datadict = {}
#        datadict["ECU"] = {}
#        datadict["Inverters"] = []
        (myhost, myport) = self.server.server_address
        rec = self.request.recv(1024)
        try:
            if rec:
                _LOGGER.warning(f"From ECU @{myhost}:{myport} - {rec}")
                # Build data dictionary
                decrec = rec.decode('utf-8')
                # walk through the ECU
                if decrec[0:7] == "APS18AA":
                    datadict = {"ECU": {"ECU-ID": decrec[18:30],
                        "Current power": int(decrec[30:42]) / 100,
                        "Lifetime Energy": int(decrec[42:60]) / 10,
                        "datetimestamp": str(datetime.strptime(decrec[60:74], '%Y%m%d%H%M%S')),
                        "Online inverters": int(decrec[74:77])},
                        "Inverters": []}
                    # walk through the inverters
                    idx = 0
                    # walk through the inverters
                    for m in re.finditer(r'END\d+', decrec):
                        datadict["Inverters"].append({
                            "Iid": str(decrec[m.start()+3:m.start()+15]),
                            "V": int(decrec[m.start()+17:m.start()+20]),
                            "F": int(decrec[m.start()+20:m.start()+25]) / 10,
                            "T": int(decrec[m.start()+25:m.start()+28]) - 100})
                        # walk through the channels of 2-channel inverters
                        if str(decrec[m.start()+3:m.start()+15][:3]) in ['406', '407', '408', '409', '703', '706']:
                            datadict['Inverters'][idx]['DC1'] = int(decrec[m.start()+51:m.start()+54]) / 10
                            datadict['Inverters'][idx]['A1'] = int(decrec[m.start()+60:m.start()+63]) / 100
                            datadict['Inverters'][idx]['P1'] = str(decrec[m.start()+63:m.start()+66])
                            datadict['Inverters'][idx]['DC2'] = int(decrec[m.start()+71:m.start()+74]) / 10
                            datadict['Inverters'][idx]['A2'] = int(decrec[m.start()+80:m.start()+83]) / 100
                            datadict['Inverters'][idx]['P2'] = str(decrec[m.start()+83:m.start()+86])
                        # walk through the channels of 4-channel inverters
                        if str(decrec[m.start()+3:m.start()+15][:3]) in ['801', '802', '806']:
                            datadict['Inverters'][idx]['DC1'] = int(decrec[m.start()+51:m.start()+54]) / 10
                            datadict['Inverters'][idx]['A1'] = int(decrec[m.start()+60:m.start()+63]) / 100
                            datadict['Inverters'][idx]['P1'] = str(decrec[m.start()+63:m.start()+66])

                            datadict['Inverters'][idx]['DC2'] = int(decrec[m.start()+71:m.start()+74]) / 10
                            datadict['Inverters'][idx]['A2'] = int(decrec[m.start()+80:m.start()+83]) / 100
                            datadict['Inverters'][idx]['P2'] = str(decrec[m.start()+83:m.start()+86])

                            datadict['Inverters'][idx]['DC3'] = int(decrec[m.start()+91:m.start()+94]) / 10
                            datadict['Inverters'][idx]['A3'] = int(decrec[m.start()+100:m.start()+103]) / 100
                            datadict['Inverters'][idx]['P3'] = str(decrec[m.start()+103:m.start()+106])

                            datadict['Inverters'][idx]['DC4'] = int(decrec[m.start()+111:m.start()+114]) / 10
                            datadict['Inverters'][idx]['A4'] = int(decrec[m.start()+120:m.start()+123]) / 100
                            datadict['Inverters'][idx]['P4'] = str(decrec[m.start()+123:m.start()+126])
                        idx += 1
                    _LOGGER.warning (f"Data Dictionary = {datadict}")
                    #ECUProxySensor(ecu_proxy_current_power) == int(decrec[30:42]) / 100
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("3.67.1.32", myport)) # don't use ecu.apsystemsema.com or it will loop
            sock.sendall(rec)
            response = sock.recv(1024)
            _LOGGER.warning(f"Response from EMA: {response}\n")
            sock.close()
            self.request.send(response)
        except Exception as e:
            LOGGER.warning(f"Exception error = {e}")


async def async_start_proxy(config: dict):
    """Setup the listeners and threads."""
    host = config['host']
    try:
        listener_1 = socketserver.TCPServer((host, 8995), PROXYSERVER)
        thread_1 = threading.Thread(target=listener_1.serve_forever)
        listener_2 = socketserver.TCPServer((host, 8996), PROXYSERVER)
        thread_2 = threading.Thread(target=listener_2.serve_forever)
        listener_4 = socketserver.TCPServer((host, 9220), PROXYSERVER)
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

#========= part to create the sensors dynamically? =================
#async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
#    sensors = []
#    async_add_entities(sensors)
#    _LOGGER.warning("hello world")
#===============================================================================

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    data_dict = entry.as_dict().get('data', {})
    _LOGGER.warning(f"Step 4: after HA restart, start proxy: {data_dict}")
    await async_start_proxy(data_dict)
    
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
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
