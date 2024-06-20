# APsystems ECU Proxy

### &#x1F534; This integration is under construction

## Main purpose
This integration intercepts and collects data from your APsystems driven PV installation. 
The received data from the ***E***nergy ***C***ommunication ***U***nit is being received and first forwarded to APsystems ***E***nergy ***M***onitoring and ***A***nalysis website.
Data is then being analyzed for use in Home Assistant so it doesn't disturb the regular process of the ECU sending data to EMA.

## Prerequisites
- An APsystems ECU device starting with ECU-ID 2160 (might be compatible with other ECU types, I don't know yet but suppose it will - let me know)
- PiHole, AdGuard or Unifi controller (from version 8.2.93) running as add-on installed on Home Assistant (or something else to rewrite DNS)
- IP-address running the proxy

## Install the integration

## Rewrite DNS traffic

## Data collected
