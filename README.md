[![Validate with hassfest](https://github.com/HAEdwin/homeassistant-apsystems_ecu_proxy/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/HAEdwin/homeassistant-apsystems_ecu_proxy/actions/workflows/hassfest.yaml)
[![Validate with HACS](https://github.com/HAEdwin/homeassistant-apsystems_ecu_proxy/actions/workflows/validatewithhacs.yml/badge.svg)](https://github.com/HAEdwin/homeassistant-apsystems_ecu_proxy/actions/workflows/validatewithhacs.yml)

![Home Assistant Dashboard](https://github.com/HAEdwin/homeassistant-apsystems_ecu_proxy/blob/main/Capture.PNG)
# APsystems ECU Proxy
Works and tested with the ECU-R (2160....) if the integration works for your ECU model (ECU-B?), please let me know which model you own!

**The integration is not compatible with:**
- the ECU-C https://github.com/HAEdwin/homeassistant-apsystems_ecu_proxy/issues/2
- the ECU-R 2162.... https://github.com/HAEdwin/homeassistant-apsystems_ecu_proxy/issues/13

## Background & acknowledgement
This integration intercepts and collects data from your APsystems driven PV installation. 
The data from the ***E***nergy ***C***ommunication ***U***nit is first being received by this integration and then passed directly on to APsystems ***E***nergy ***M***onitoring and ***A***nalysis website.
Any returned data from EMA is directly sent back to the ECU. After this, the data obtained is then being analyzed for use in Home Assistant so it doesn't disturb the regular process of the ECU sending data to EMA and vice versa.
This custom integration was made possible by the hard work of @msp1974 - thank you for solving the challenges that this integration presented!

## Prerequisites
- An APsystems ECU device starting with ECU-ID 2160 (might be compatible with other ECU types except for the ECU-C https://github.com/HAEdwin/homeassistant-apsystems_ecu_proxy/issues/2).
- PiHole, AdGuard running as add-on installed on Home Assistant or something else like Unifi controller (from network version 8.2.93 or higher) to rewrite DNS.
- Working HACS installation and GitHub account (manual installation is possible).
- An ECU-R, ethernet or WiFi connected.
- Inverters need to be online (daylight) for quick results.

## Install the integration
_Note for pre-v1.1.0 users:
Take into account the changed workflow in which no migration provision has been made.
It is best to remove and reinstall the integration via HACS._

The installation of custom integrations is done in three steps (assuming HACS is already installed):

**1. Downloading the custom integration**
- Navigate to HACS and choose the overflow menu in the top right corner of the Home Assistant Community Store.
- Choose Custom repositories and paste the url: https://github.com/HAEdwin/homeassistant-apsystems_ecu_proxy in the Repository field.
- Choose Type > Integration and select the [Add]-button.
From this point it might allready have been added to the personal store repository.
- In HACS search for APsystems and the APsystems ECU Proxy will be listed in de Available for download section.
- From the overflow menu on the right select [Download] and automatically the latest version will be listed for download so choose [Download].
- HA Settings will now show the repair action that a Restart is required, submit the action and HA will restart.

After HA's restart the downloaded custom integration will be detected by HA.
The integration will need to be configured in order to fully integrate it in HA and make it work.

**2. Integrating the custom integration into Home Assistant**
- Navigate to [Settings] > [Devices & services] and choose the button [+ ADD INTEGRATION].
- In Search for a brand name, choose APsystems and the APsystems ECU Proxy will be listed.
- Select it and the Configuration dialog will show, defaults are fine right now so choose [SUBMIT].

**3. Rewrite DNS traffic**
- Use PiHole, AdGuard or Unifi (or any other preferred method) to rewrite DNS. For example in AdGuard: Navigate to > Filters > DNS Rewrites > Add DNS rewrite > For domain name enter: ecu.apsystemsema.com > for IP-address enter: IP-address where the integration runs.
- Within 6 minutes data should be received by the integration and entities will appear. In worst case scenario you will have to wait for 10 minutes before all the devices and entities will show up. After that you can start the fun part of adding the entities to the dashboard.
- You can verify if the rewrite works by sending a ping to ecu.apsystemsema.com, response should be the previously entered IP-address from your local HA install (or where this integration runs).

## Available sensors
- ECU: Current Power, Daily Max Power, Lifetime Max Power, Hourly Energy Production, Daily Energy Production, Lifetime Energy Production, Inverters Online, Lifetime Energy, Last Update
- Inverters: Temperature, Frequency, Power per channel, Current per channel, Voltage per channel

_Note that the sensors ending with "Production" are calculated sensors and results may differ from EMA._

## Q & A
- Q: I see different results from the integration and at EMA, why is that?
A: Partly it depends on when you compare the results. If the inverters are offline, the ECU will start a maintenance cycle. The completeness of data transfer is checked and missed data at EMA is resent to EMA. This means that the results may not match each other better until the next day. Values ​​may differ because the time span over which results are calculated is different. However, differences should not be large because both the custom integration and EMA use the same data supplied by the ECU.
- Q: I get the message "No devices or entities" after installing the integration?
A: The inverters are off-line, without them the integration is unable to determen what hardware is connected to the ECU.
- Q: Will deleting the integration make me loose all the data (like Lifetime Energy)?
A: Yes, deleting the integration will remove the entities and their most current values - history data however is kept in de HA database.
- Q: One (or more) inverters are down, what is wrong?
A: Check that the ECU is properly positioned relative to the inverters. It may happen that the inverter works normally, but the reception on the ECU side is not optimal. Also look at the ECU current Power parameter, which should be a good indication of the total power that the installation could produce at that moment.
