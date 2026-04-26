"""Config flow for Kuchnia Vikinga."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class KuchniaVikingaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kuchnia Vikinga."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Single-step flow — there's nothing to configure."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Kuchnia Vikinga", data={})
