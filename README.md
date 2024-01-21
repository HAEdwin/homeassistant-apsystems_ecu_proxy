# APSystems ECU Proxy

### &#x1F534; Warning: This integration is under construction and in very early stages - use at your own risk!

## Main purpose
The proxy will intercept traffic going from the ECU device to the EMA server and vice versa.

ToDo
- Interpret the data so that it can be set to sensors
- Use the checksum: verify the datalength (in cases of large PV installations) or enlarge the buffer size

## Prerequisites
- ECU-R starting with ECU-ID 2160 (might be compatible with ECU-B, I don't know)
- PiHole or AdGuard running as add-on installed on Home Assistant

# Description
This short script should enable APSystems ECU users to work cloudless. 
Under normal circumstances, the ECU will stop functioning when apsystems.com domains are blocked. This Python 3 script causes the ECU to get simulated responses (as if the response came from the EMA cloud). APSystems have put a lot of work into keeping your data on the EMA cloud correctly up to date but did not give users the option not to do so without the ECU going down.

Every five minutes the ECU sends recent data to ecu.apsystemsema.com alternately via port 8995, 8996 and 8997. These ports are opened for a short amount of time to await response and is then being closed again. So EMA site swiftly responds with a timestamp of the last received data (this is usually the recent data - 5 minutes) to the ECU. The ECU now knows it has fully synchronized with the EMA site and also is aware of having an internet connection with EMA. When the inverters are offline, the ECU sends pull requests to EMA for missing data (if applicable). The EMA site responds with a timestamp of missing data after which the ECU will respond serving the missing data to EMA. 
This is of course not the complete functional description of how the ECU works, but this part covers the most important functions to keep the ECU running and handle exceptions on normal operations during the up- and downtime of inverters. This works the same for unattended OTA firmware updates, the ECU sends a pull request and if firmware is available leaves the port open to download and install firmware. 


# Why cloudless
- Firmware updates are being pushed to my ECU-R without any notice or release notes 
- I want to prevent others from being able to shut down my PV installation
- All parameters (even more than the EMA cloud holds) is present and is being read from the ECU using the HomeAssistant integration at https://github.com/ksheumaker/homeassistant-apsystems_ecur
- Ability to privately own the produced data

# Disadvantage
- If you are not using HA, no large repository of historical data and (trend-)analysis is available
- No ECU and Inverter (Over The Air) firmware updates
- You'll have to know how to reroute traffic

# Advantage
- You can use this method to optain the data directly from the ECU without having to scrape the EMA website and then push it to PVOutput for example (you will be missing some inverter parameters like signal strengths and temperatures though)
- No unsollicited OTA firmware updates for ECU or Inverters

# How to use
1. DNS rewrite \*.apsystemsema.com to a local host that is running this script (check if a ping to ecu.apsystemsema.com resolves to your host IP-address)
2. Block all (future) communication with APSystems and EMA system. Current list of used domains include:
* apsystemsema.cn
* ecuna.apsema.com
* ecueu.apsema.com
* ecu2.apsema.com
* \*.apsystemsema.cn
* \*.apsema.com
* \*.apsystems.com
* ...
3. Run the script for example with PyCharm or from within terminal type: python3 main.py at a host which is continuously running (Raspberry Pi or something)
4. You're done

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
