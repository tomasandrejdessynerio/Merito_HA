"""Config Flow for MeriTO Technologies integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from homeassistant.components.mqtt import DOMAIN as MQTT_DOMAIN

from .const import DOMAIN, CONF_MQTT_DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MQTT_DOMAIN, default="DEMO"): cv.string,
    }
)


class MeritoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for MeriTO Technologies."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial configuration step shown in HA GUI."""
        errors: dict[str, str] = {}

        # Check MQTT dependency via loaded integrations
        if not self.hass.config_entries.async_entries(MQTT_DOMAIN):
            return self.async_abort(reason="mqtt_not_available")

        if user_input is not None:
            mqtt_domain = user_input[CONF_MQTT_DOMAIN].strip().upper()

            if not mqtt_domain:
                errors[CONF_MQTT_DOMAIN] = "invalid_domain"
            else:
                await self.async_set_unique_id(f"merito_{mqtt_domain}")
                self._abort_if_unique_id_configured()

                _LOGGER.info(
                    "MeriTO Technologies: creating config entry for domain '%s'",
                    mqtt_domain,
                )
                return self.async_create_entry(
                    title=f"MeriTO Technologies ({mqtt_domain})",
                    data={CONF_MQTT_DOMAIN: mqtt_domain},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "mqtt_domain": "DEMO",
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Allow reconfiguration of an existing entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mqtt_domain = user_input[CONF_MQTT_DOMAIN].strip().upper()
            if not mqtt_domain:
                errors[CONF_MQTT_DOMAIN] = "invalid_domain"
            else:
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    data={CONF_MQTT_DOMAIN: mqtt_domain},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
