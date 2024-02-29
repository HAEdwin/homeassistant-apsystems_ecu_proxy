""" module that processes incoming data pushed from the ECU onto ports """

from socketserver import BaseRequestHandler
import re
import socket
import logging
from datetime import datetime
import traceback
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

data = {}

# dit deel werkt
class PROXYSERVER(BaseRequestHandler):
    """ Class provides data """
    def handle(self):
        self.ecu_id = None
        (myhost, myport) = self.server.server_address
        rec = self.request.recv(1024)
        try:
            _LOGGER.warning(f"From ECU @{myhost}:{myport} - {rec}")
            decrec = rec.decode('utf-8')
            # Build data dictionary
            if decrec[0:7] == "APS18AA": # walk through the ECU
                data["timestamp"] = str(datetime.strptime(decrec[60:74], '%Y%m%d%H%M%S'))
                data["ecu-id"] = decrec[18:30]
                if data["ecu-id"][:4] == "2160":
                    data["model"] = "ECU-R"
                if data["ecu-id"][:4] == "2162":
                    data["model"] = "ECU-R pro"
                if data["ecu-id"][:4] == "2163":
                    data["model"] = "ECU-B"
                if data["ecu-id"][:3] == "215":
                    data["model"] = "ECU-C"
                data["lifetime_energy"] = int(decrec[42:60]) / 10
                data["current_power"] = int(decrec[30:42]) / 100
                data["qty_of_online_inverters"] = int(decrec[74:77])
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
                data["inverters"] = inverters
                _LOGGER.warning (f"Data Dictionary = {data}")
#            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#            sock.connect(("3.67.1.32", myport)) # don't use ecu.apsystemsema.com or it will loop
#            sock.sendall(rec)
#            response = sock.recv(1024)
#            _LOGGER.warning(f"Response from EMA: {response}\n")
#            sock.close()
#            self.request.send(response)
        except Exception:
            _LOGGER.warning(f"Exception error = {traceback.format_exc()}")
