"""Config flow for SA Speed Cameras."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_LOOKUP_PATH,
    CONF_SCAN_INTERVAL,
    DEFAULT_LOOKUP_PATH,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_LOOKUP_PATH, default=defaults.get(CONF_LOOKUP_PATH, DEFAULT_LOOKUP_PATH)
            ): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES),
            ): vol.All(int, vol.Range(min=15, max=1440)),
        }
    )


class SASpeedCameraConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SA Speed Cameras. Single-instance integration."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="SA Speed Cameras", data=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return SASpeedCameraOptionsFlow(config_entry)


class SASpeedCameraOptionsFlow(config_entries.OptionsFlow):
    """Handle options (lookup file path, scan interval) after setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(defaults))
