import logging
import asyncio
import socketserver
from .proxy import PROXYSERVER
import threading

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

# TODO List the platforms that you want to support
# elk platform verwijst naar een module, bijvoorbeeld sensor.py 
PLATFORMS = ["sensor"]

class APSystemsECUProxyInvalidData(Exception):
    pass

async def async_setup(hass: HomeAssistant, config: dict):
    # Set up the component
    _LOGGER.warning(f"step 2: async_setup from __init__.py  config={config}" )
    
    
    return True

async def async_start_proxy(config: dict):
    _LOGGER.warning("aangeroepen: async_start_proxy from __init__.py")
    """Setup the listeners and threads."""
    host = config['host']
    _LOGGER.warning(f"host={config['host']}")
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
    except Exception as err:
        raise APSystemsECUProxyInvalidData(err)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
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
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
