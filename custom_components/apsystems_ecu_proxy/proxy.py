import socket
import socketserver
from socketserver import BaseRequestHandler




class PROXYSERVER(BaseRequestHandler):
    def handle(self):
        (myhost, myport) = self.server.server_address
        #global ecu_current_power
        rec = self.request.recv(1024)
        if rec:
            logging.warning(f"From ECU @{self.client_address[0]}:{myport} - {rec}")
            # Data to MQTT sensors
            try:
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                start = '05:00:00'
                end = '22:00:00'
                # Is it inverter data?
                if (rec[0:7].decode('ASCII')) == "APS18AA" and current_time > start and current_time < end:
                    ecu_current_power = int(rec[30:42])/100
                    #inverter_index = rec.decode('ASCII').find('END')
                    #logging.warning (inverter_index)
                    
                    #    client.publish("homeassistant/apsystems/ecu/ecuid", int(rec[18:30]))
                    #    client.publish("homeassistant/apsystems/ecu/current_power", int(rec[30:42])/100)
                    #    client.publish("homeassistant/apsystems/ecu/lifetime_energy", int(rec[42:60])/10)
                    #    client.publish("homeassistant/apsystems/ecu/inverters_online", int(rec[74:77]))
                    
            except Exception as e:
                logging.warning(e)

            # forward message to EMA
            if myport == 8995 or myport == 8996:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("3.67.1.32", myport)) # don't use ecu.apsystemsema.com due to rewrite it will loop
                sock.sendall(rec)
                response = sock.recv(1024)
                logging.warning(f"From EMA: {response}\n")
                sock.close()
                self.request.send(response) # stuur EMA response door naar ECU

            # return messages to ECU for cloud independence
            if rec[0:17].decode('ASCII') == "ECU11008000010001":
                logging.warning("Sending fake response 1 to ECU\n")
                self.request.send(b'ECU11003000010001END0\x00\x00\x00\x00\x00\x00END')
            elif rec[0:32].decode('ASCII') == "ECU1100320004[ECU-ID]0003END":
                logging.warning("Sending fake response 2 to ECU\n")
                self.request.send(b'ECU1100990004[ECU-ID]0003END0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00000END')
            elif rec[0:32].decode('ASCII') == "ECU1100320004[ECU-ID]0001END":
                logging.warning("Sending fake response 3 to ECU\n")
                self.request.send(b'ECU1100990004[ECU-ID]0001END0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00000END')
