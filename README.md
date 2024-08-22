![Home Assistant Dashboard](https://github.com/HAEdwin/homeassistant-apsystems_ecu_proxy/blob/main/impression.jpg)
# APsystems ECU Proxy

### &#x1F534; This integration is under construction
Works and tested with the ECU-R (2160....) if the integration works for your ECU, please let me know!

## Main purpose
This integration intercepts and collects data from your APsystems driven PV installation. 
The data from the ***E***nergy ***C***ommunication ***U***nit is first being received by this integration and then passed on to APsystems ***E***nergy ***M***onitoring and ***A***nalysis website.
The optained data is then being analyzed for use in Home Assistant so it doesn't disturb the regular process of the ECU sending data to EMA and vice versa.

## Prerequisites
- An APsystems ECU device starting with ECU-ID 2160 (might be compatible with other ECU types, I don't know yet but suppose it will - if it does not let me know and show me some logging!)
- PiHole, AdGuard running as add-on installed on Home Assistant or something else like Unifi controller (from version 8.2.93) to rewrite DNS.

## Install the integration

## Rewrite DNS traffic
Use PiHole, AdGuard of Unifi (or any other preferred method) to rewrite DNS. For example in AdGuard: Navigate to > Filters > DNS Rewrites > Add DNS rewrite > For domain name enter: ecu.apsystemsema.com > for IP-address enter: IP-address where the integration runs.
Within 6 minutes data should be received by the integration and entities will appear.

## Available sensors
- ECU: Power, Number of inverters online, Lifetime Energy, Last update
- Inverters: Temperature, Frequency, Power per channel, Current per channel, Voltage per channel
- Calculated: Hourly Energy produced, Daily Energy produced, Lifetime Energy produced, Daily Max Power, Lifetime Max Power.

## Q & A
- Q: I see different results from the integration and at EMA, why is that?
A: Partly it depends on when you compare the results. If the inverters are offline, the ECU will start a maintenance cycle. The completeness of data transfer is checked and missed data at EMA is resent to EMA. This means that the results may not match each other better until the next day. Values ​​may differ because the time span over which results are calculated is different. However, differences should not be large because both the integration and EMA use the same data.
- Q: I get the message "No devices or entities" after installing the integration?
A: The inverters are off-line, without them the integration is unable to determen what hardware is connected to the ECU.
- Q: Will deleting the integration make me loose all the data (like Lifetime Energy)?
A: Yes, deleting the integration will remove the entities and their most current values - history data however is kept in de HA database.
- Q: On what day does the new week start?
A: It starts on monday.
