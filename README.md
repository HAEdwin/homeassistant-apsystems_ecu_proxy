# APSystems ECU Proxy

### &#x1F534; This integration is under construction

## Main purpose
This integration is a HUB and will intercept and route traffic going from the ECU device to the EMA server and vice versa.
It collects data from a PV installation to show in Home Assistant. The data comes from multiple devices (inverters and an ***E***nergy ***C***ommunication ***U***nit that functions as a hub).

## Prerequisites
- An APSystems ECU device starting with ECU-ID 2160 (might be compatible with other ECU types, I don't know yet but suppose it will)
- PiHole or AdGuard running as add-on installed on Home Assistant or elsewhere to rewrite the DNS
- Unifi controller (from version 8.2.93)

## What the integration does
It listens on ports for incoming data. About every five minutes the ECU sends PV data to ecu.apsystemsema.com alternately via port 8995, 8996 and 8997.
By rewriting the URL designation to the IP-Address from this Proxy integration, the traffic is intercepted, interpreted and send through to the receiver (ecu.apsystemsema.com)
Same goes for the returned data from the EMA site to the ECU device, this needs no interpretation and is directly returned to the ECU.

***The datastring looks like:***

b'APS18AA302AAAAAAA121600006413600000001900000000000000002127920240206112214002000000END4080001111780722800500113000000329000000000001003380050014090170020033900500141901800END80600001122308228005001150000001457000000000010031101000230902900200342012003070038003003340140035690450040032901400343704300END\n

***I converterted the data to look like this in a dictionary that is being updated every 5 minutes:***

{'ECU': {'ECU-ID': '216000064136', 'Current power': 190.0, 'Lifetime Energy': 2127.9, 'datetimestamp': '2024-02-06 11:22:14', 'Online inverters': 2}, 'Inverters': [{'Iid': '408000111178', 'V': 228, 'F': 50.0, 'T': 13, 'DC1': 33.8, 'A1': 4.09, 'P1': '017', 'DC2': 33.9, 'A2': 4.19, 'P2': '018'}, {'Iid': '806000011223', 'V': 228, 'F': 50.0, 'T': 15, 'DC1': 31.1, 'A1': 3.09, 'P1': '029', 'DC2': 34.2, 'A2': 0.7, 'P2': '038', 'DC3': 33.4, 'A3': 5.69, 'P3': '045', 'DC4': 32.9, 'A4': 4.37, 'P4': '043'}]}

Iid=Inverter id, V=Voltage, F=Frequency, T=Temperature, DC=Direct Current, A=Current, P=Power
