import logging

import voluptuous as vol

from homeassistant import config_entries, core, exceptions


from .const import DOMAIN
from .__init__ import async_start_proxy, APSystemsECUProxyInvalidData


_LOGGER = logging.getLogger(__name__)

# Schema heeft alleen de naam van de host nog niets anders
DATA_SCHEMA = vol.Schema({"host": str})


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect."""
    _LOGGER.debug(f"step 1: validate_input from config_flow.py data={data}")
    try:
        await async_start_proxy(data)
    except APSystemsECUProxyInvalidData as err:
        # raise friendly error after wrong input
        raise CannotConnect
    return {"title": "APSystems ECU Proxy"}        


class DomainConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for warmup4ie."""

    VERSION = 1
    # TODO pick one of the available connection classes in homeassistant/config_entries.py
    CONNECTION_CLASS = config_entries.CONN_CLASS_UNKNOWN

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        # Only allow one instance of the hub allowed
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        # Validate user input
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
