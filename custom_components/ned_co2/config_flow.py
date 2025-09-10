from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from .const import *

class NedConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="NED CO₂", data={
                CONF_API_KEY: user_input[CONF_API_KEY],
            }, options={
                CONF_POINT: user_input.get(CONF_POINT, DEFAULT_POINT),
                CONF_GRANULARITY: user_input.get(CONF_GRANULARITY, DEFAULT_GRANULARITY),
                CONF_WINDOW_DAYS: user_input.get(CONF_WINDOW_DAYS, DEFAULT_WINDOW_DAYS),
                CONF_LOCAL_TZ_FILTER: user_input.get(CONF_LOCAL_TZ_FILTER, DEFAULT_LOCAL_TZ_FILTER),
            })

        schema = vol.Schema({
            vol.Required(CONF_API_KEY): str,
            vol.Optional(CONF_POINT, default=DEFAULT_POINT): int,
            vol.Optional(CONF_GRANULARITY, default=DEFAULT_GRANULARITY): vol.In([4,5]),
            vol.Optional(CONF_WINDOW_DAYS, default=DEFAULT_WINDOW_DAYS): vol.All(int, vol.Range(min=1, max=3)),
            vol.Optional(CONF_LOCAL_TZ_FILTER, default=DEFAULT_LOCAL_TZ_FILTER): bool,
        })
        return self.async_show_form(step_id="user", data_schema=schema)
