import logging
import voluptuous as vol
import asyncio
from homeassistant import config_entries, exceptions
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """First start of integration settings."""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get stored configuration data to present in async_step_init."""
        _LOGGER.debug("async_get_options_flow called: %s", config_entry)
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """First step: Initial set-up of integration options."""
        _LOGGER.debug("async_step_user")
        schema = vol.Schema({
            vol.Required("ema_host", default="3.67.1.32"): str,
            vol.Required("message_ignore_age", default="1800"): str,
            vol.Required("max_stub_interval", default="300"): str,
            vol.Required("no_update_timeout", default="600"): str,
            vol.Required("send_to_ema", default=True): bool,
        })

        if user_input is not None:
            if await OptionsFlowHandler.validate_ip(user_input["ema_host"]):
                return self.async_create_entry(title="APsystems ECU proxy", data=user_input)
            else:
                return self.async_show_form(
                    step_id="user",
                    data_schema=schema,
                    errors={"base": "Could not connect to the specified EMA host."},
                )
        return self.async_show_form(step_id="user", data_schema=schema)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Regular change of integration options."""
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Second step: Altering the integration options."""
        current_options = (
            self.config_entry.data 
            if not self.config_entry.options 
            else self.config_entry.options
        )
        _LOGGER.debug("async_step_init with options: %s", current_options)
        
        keys = [
            "ema_host", 
            "message_ignore_age", 
            "max_stub_interval", 
            "no_update_timeout", 
            "send_to_ema"
        ]
        schema = vol.Schema({
            vol.Required(key, default=current_options.get(key)): str if key != "send_to_ema" else bool 
            for key in keys
        })

        if user_input is not None:
            ema_host = user_input["ema_host"]
            if await self.validate_ip(ema_host):
                updated_options = current_options.copy()
                updated_options.update(user_input)
                return self.async_create_entry(title="", data=updated_options)
            else:
                return self.async_show_form(
                    step_id="init",
                    data_schema=schema,
                    errors={"base": "Could not connect to the specified EMA host."},
                )
        return self.async_show_form(step_id="init", data_schema=schema)

    @staticmethod
    async def validate_ip(ip_address: str) -> bool:
        try:
            await asyncio.wait_for(asyncio.open_connection(ip_address, 8995), timeout=5.0)
            return True
        except (OSError, asyncio.TimeoutError):
            return False
