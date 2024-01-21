# APSystems Proxy

### &#x1F534; Warning: This integration is under construction and in very early stages - use at your own risk!

## Main purpose
The proxy will intercept traffic going from the ECU device to the EMA server and vice versa.

ToDo
- Interpret the data so that it can be set to sensors
- Use the checksum: verify the datalength (in cases of large PV installations) or enlarge the buffer size

## Prerequisites
- ECU-R starting with ECU-ID 2160 (might be compatible with ECU-B, I don't know)
- PiHole or AdGuard running as add-on installed on Home Assistant

## Installation
- If you haven't allready got one: Create a folder named "custom_components" in the config folder
- Create a subfolder in the custom_components folder called "apsystems_ecu_proxy"
- Download the code and place it in the folder last mentioned
- Restart Home Assistant (important!)

- Restart Home Assistant once more and the proxy will load
- Finally: Use PiHole or AdGuard to rewrite DNS ecu.apsystemsema.com to your HA instance IP-addess
- Until now you'll only find data messages from your ECU and the EMA server in the log every 5 minutes (when sun is up) or 15 minutes (when sun is down)

## How it works (more or less)
From what I know there are some data verifications build in to make sure data is complete and correct. After sunset these checks are performed every five minutes. When the datacheck is complete the communication takes place every 15 minutes. Around 02:00 in the morning, firmware and maintenance checks are being done. Until sunset interval remains 15 minutes until the first inverter is up. This is the part we use/need.
When the inverter(s) are activated by the sun, data is sent to EMA on one of two randomly choosen ports 8995 and 8996 every five minutes. The EMA sites responds with a current timestamp minus 5 minutes to indicate all is well.
After three updates, the ECU initiates a "question" on what I think is the control port 8997. The EMA site responds with the registered ECU-ID and all is well. Then the cycle repeats at sundown.

## Where I need help
- Finding the purpose of data not yet mapped to current values
- Further develop the integration to a useful one, add sensors and such
