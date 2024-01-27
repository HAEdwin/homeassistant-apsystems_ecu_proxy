import logging
import asyncio
# Keep these ============
import socket
import socketserver
import threading
from socketserver import BaseRequestHandler
# =======================
from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
#from .proxy import PROXYSERVER
from datetime import datetime
import re

from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)

# TODO List the platforms that you want to support
# elk platform verwijst naar een module, bijvoorbeeld sensor.py 
PLATFORMS = ["sensor"]

class APSystemsECUProxyInvalidData(Exception):
    pass

class PROXYSERVER(BaseRequestHandler):
    def handle(self):
        # Create an instance of the sensor
        #my_sensor = MySensor()
        datadict = {}
        datadict["ECU"] = {}
        datadict["Inverters"] = []

        (myhost, myport) = self.server.server_address
        #global ecu_current_power
        rec = self.request.recv(1024)
        if rec:
            _LOGGER.warning(f"From ECU @{self.client_address[0]}:{myport} - {rec}")
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
                for m in re.finditer('END\d+', decrec):
                    datadict["Inverters"].append({
                        "InverterID": str(decrec[m.start()+3:m.start()+15]),
                        "Voltage": int(decrec[m.start()+17:m.start()+20]),
                        "Frequency": int(decrec[m.start()+20:m.start()+25]) / 10,
                        "Temperature": int(decrec[m.start()+25:m.start()+28]) - 100})
                    # walk through the channels
                    if str(decrec[m.start()+3:m.start()+15][:3]) in ['406', '407', '408', '409', '703', '706']:
                        datadict['Inverters'][idx]['Power1'] = str(decrec[m.start()+63:m.start()+66])
                        datadict['Inverters'][idx]['Power2'] = str(decrec[m.start()+83:m.start()+86])

                    if str(decrec[m.start()+3:m.start()+15][:3]) in ['801', '802', '806']:
                        datadict['Inverters'][idx]['Power1'] = str(decrec[m.start()+63:m.start()+66])
                        datadict['Inverters'][idx]['Power2'] = str(decrec[m.start()+83:m.start()+86])
                        datadict['Inverters'][idx]['Power3'] = str(decrec[m.start()+103:m.start()+106])
                        datadict['Inverters'][idx]['Power4'] = str(decrec[m.start()+123:m.start()+126])
                    idx += 1
#===============================================================================
                _LOGGER.warning(f"Data = {datadict}")

            # forward message to EMA
            #if myport == 8995 or myport == 8996:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("3.67.1.32", myport)) # don't use ecu.apsystemsema.com due to rewrite it will loop
                sock.sendall(rec)
                response = sock.recv(1024)
                _LOGGER.warning(f"Response from EMA: {response}\n")
                sock.close()
                self.request.send(response) # stuur EMA response door naar ECU
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

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    data_dict = entry.as_dict().get('data', {})
    _LOGGER.debug(f"Step 4: after HA restart, start proxy: {data_dict}")
    await async_start_proxy(data_dict)
    
    """Set up proxy from a config entry."""
    # TODO Store an API object for your platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

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
