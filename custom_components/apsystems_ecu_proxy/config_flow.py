import logging
import voluptuous as vol
import asyncio
from homeassistant import config_entries, exceptions
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        schema = vol.Schema({
            vol.Required("EMA host", default="3.67.1.32"): str,
            vol.Required("Message ignore age", default="1800"): str,
            vol.Required("Max stub interval", default="300"): str,
            vol.Required("No update timeout", default="600"): str,
            vol.Optional("Send to EMA", default=True): bool,
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
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        current_options = self.config_entry.options or {}
        schema = vol.Schema({
            vol.Optional("EMA host", default=current_options.get("ema_host", "3.67.1.32")): str,
            vol.Optional("Message ignore age", default=current_options.get("Message ignore age", "1800")): str,
            vol.Optional("Max stub interval", default=current_options.get("Max stub interval", "300")): str,
            vol.Optional("No update timeout", default=current_options.get("No update timeout", "600")): str,
            vol.Optional("Send to EMA", default=current_options.get("Send to EMA", True)): bool,
        })

        if user_input is not None:
            ema_host = user_input["EMA host"]
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
