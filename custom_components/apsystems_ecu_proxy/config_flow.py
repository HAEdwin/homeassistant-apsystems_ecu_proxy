"""Config flow to setup component"""
import logging
import voluptuous as vol
from homeassistant import config_entries, exceptions
from .const import DOMAIN
from .__init__ import APSystemsECUProxyInvalidData, async_setup_entry


_LOGGER = logging.getLogger(__name__)

# Schema contains name of host only
DATA_SCHEMA = vol.Schema({"host": str})


async def validate_input(data):
    """Validate the user input allows us to connect."""
    _LOGGER.debug("step 1: validate_input from config_flow.py data = %s",data)
    try:
        async_setup_entry
    except APSystemsECUProxyInvalidData as err:
        # raise friendly error after wrong input
        raise CannotConnect from err
    return {"title": "APSystems ECU Proxy"}

class DomainConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow"""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        # Only allow one instance of the hub allowed
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        # Validate user input
        if user_input is not None:
            try:
                info = await validate_input(user_input)
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
