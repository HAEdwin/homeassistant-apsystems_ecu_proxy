import socket
import socketserver
from socketserver import BaseRequestHandler

class PROXYSERVER(BaseRequestHandler):
    def handle(self):
        # Create an instance of the sensor
        #my_sensor = MySensor()
        (myhost, myport) = self.server.server_address
        #global ecu_current_power
        rec = self.request.recv(1024)
        if rec:
            _LOGGER.warning(f"From ECU @{self.client_address[0]}:{myport} - {rec}")
            #try:
                # Is it inverter data?
                #if (rec[0:7].decode('ASCII')) == "APS18AA":
                    # Update the sensor's state
                    #_LOGGER.warning(f"Current power: {int(rec[30:42])/100} W")
                    #my_sensor = int(rec[30:42])/100
                    #my_sensor.update()
                    #inverter_index = rec.decode('ASCII').find('END')
                    #_LOGGER.warning (inverter_index)
            #except Exception as e:
            #    _LOGGER.warning(e)

            # forward message to EMA
            if myport == 8995 or myport == 8996:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(("3.67.1.32", myport)) # don't use ecu.apsystemsema.com due to rewrite it will loop
                    sock.sendall(rec)
                    response = sock.recv(1024)
                    _LOGGER.warning(f"Current power: {int(rec[30:42])/100}W    Response from EMA: {response}\n")
                    sock.close()
                    self.request.send(response) # stuur EMA response door naar ECU
                except Exception as e:
                    LOGGER.warning(f"Exception error = {e}")
