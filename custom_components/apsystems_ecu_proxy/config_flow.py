"""Config flow to setup component."""

import logging

import voluptuous as vol

from homeassistant.config_entries import CONN_CLASS_LOCAL_POLL, ConfigFlow
from homeassistant.exceptions import HomeAssistantError

from . import APsystemsECUProxyInvalidData
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Schema contains name of host only
DATA_SCHEMA = vol.Schema({"host": str})


async def validate_input(data):
    """Validate the user input allows us to connect."""
    _LOGGER.debug("step 1: validate_input from config_flow.py data = %s", data)
    try:
        pass
    except APsystemsECUProxyInvalidData as err:
        # raise friendly error after wrong input
        raise CannotConnect from err
    return {"title": "APsystems ECU Proxy"}


class DomainConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
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


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
