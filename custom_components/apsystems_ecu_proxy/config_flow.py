import logging
import voluptuous as vol
import asyncio
from homeassistant import config_entries, exceptions
from homeassistant.core import callback

from .const import DOMAIN, KEYS

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Integration configuration."""
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
            vol.Required(KEYS[0], default="3.67.1.32"): str,
            vol.Required(KEYS[1], default="1800"): str,
            vol.Required(KEYS[2], default="300"): str,
            vol.Required(KEYS[3], default="660"): str,
            vol.Required(KEYS[4], default=True): bool,
        })

        if user_input is not None:
            if await OptionsFlowHandler.validate_ip(user_input["ema_host"]):
                return self.async_create_entry(title="APsystems ECU proxy", data=user_input)
            else:
                return self.async_show_form(
                    step_id="user",
                    data_schema=schema,
                    errors={"base": "Could not connect to the specified EMA host"},
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
        _LOGGER.debug("async_step_init with configuration: %s", current_options)
        
        schema = vol.Schema({
            vol.Required(key, default=current_options.get(key)): (
                str if key != "send_to_ema" else bool
            )
            for key in KEYS
        })


        if user_input is not None:
            if await self.validate_ip(user_input["ema_host"]):
                updated_options = current_options.copy()
                updated_options.update(user_input)
                return self.async_create_entry(title="", data=updated_options)
            else:
                return self.async_show_form(
                    step_id="init",
                    data_schema=schema,
                    errors={"base": "Could not connect to the specified EMA host"},
                )
        return self.async_show_form(step_id="init", data_schema=schema)

    @staticmethod
    async def validate_ip(ip_address: str) -> bool:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip_address, 8995),
                timeout=3.0
            )
            # Close the connection neatly
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, asyncio.TimeoutError):
            return False
