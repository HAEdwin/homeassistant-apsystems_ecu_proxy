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
        _LOGGER.warning("async_get_options_flow called: %s", config_entry)
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """First step: Initial set-up of integration options."""
        _LOGGER.warning("async_step_user")
        schema = vol.Schema({
            vol.Required("ema_host", default="3.67.1.32"): str,
            vol.Required("message_ignore_age", default="1800"): str,
            vol.Required("max_stub_interval", default="300"): str,
            vol.Required("no_update_timeout", default="600"): str,
            vol.Required("send_to_ema", default=True): bool,
        })

        if user_input is not None:
            ema_host = user_input["ema_host"]
            if await OptionsFlowHandler.validate_ip(ema_host):
                return self.async_create_entry(title="", data=user_input)
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
        _LOGGER.warning("async_step_init with options: %s", current_options)
        
        schema = vol.Schema({
            vol.Required("ema_host", default=current_options.get("ema_host")): str,
            vol.Required("message_ignore_age", default=current_options.get("message_ignore_age")): str,
            vol.Required("max_stub_interval", default=current_options.get("max_stub_interval")): str,
            vol.Required("no_update_timeout", default=current_options.get("no_update_timeout")): str,
            vol.Required("send_to_ema", default=current_options.get("send_to_ema")): bool,
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

class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
