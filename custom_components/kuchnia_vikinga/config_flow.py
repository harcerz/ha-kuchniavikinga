"""Config flow for Kuchnia Vikinga.

One config entry per household member: each picks a `name` and a `diet`.
The diet dropdown is populated from the live menu so it always matches what
the website actually offers.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)
from homeassistant.util import slugify

from .const import CONF_DIET_SLUG, CONF_PERSON_NAME, DATA_COORDINATOR, DOMAIN
from .coordinator import fetch_menu_snapshot
from .parser import MenuSnapshot

_LOGGER = logging.getLogger(__name__)


async def _fetch_diet_options(hass) -> list[SelectOptionDict]:
    """Return diet options for a SelectSelector.

    Reuses the running coordinator's snapshot if present; otherwise does a
    one-shot fetch that does NOT register a singleton coordinator. This keeps
    aborted config flows from leaving an orphan coordinator behind.
    """
    bucket = hass.data.get(DOMAIN, {})
    coordinator = bucket.get(DATA_COORDINATOR)
    snapshot: MenuSnapshot | None = (
        coordinator.data if coordinator is not None else None
    )
    if snapshot is None or not snapshot.diets:
        snapshot = await fetch_menu_snapshot(hass)

    if not snapshot or not snapshot.diets:
        return []
    return [
        SelectOptionDict(value=slug, label=diet.name)
        for slug, diet in sorted(snapshot.diets.items(), key=lambda kv: kv[1].name.lower())
    ]


class KuchniaVikingaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add one household member as one config entry."""

    VERSION = 1

    def __init__(self) -> None:
        self._diet_options: list[SelectOptionDict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if not self._diet_options:
            try:
                self._diet_options = await _fetch_diet_options(self.hass)
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Failed to fetch diet list: %s", err)
                return self.async_abort(reason="cannot_connect")
            if not self._diet_options:
                return self.async_abort(reason="no_diets_found")

        if user_input is not None:
            name = (user_input.get(CONF_PERSON_NAME) or "").strip()
            diet_slug = user_input.get(CONF_DIET_SLUG)

            if not name:
                errors[CONF_PERSON_NAME] = "name_required"
            if not diet_slug or diet_slug not in {opt["value"] for opt in self._diet_options}:
                errors[CONF_DIET_SLUG] = "diet_invalid"

            if not errors:
                unique_id = slugify(name)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={CONF_PERSON_NAME: name, CONF_DIET_SLUG: diet_slug},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PERSON_NAME,
                        default=user_input.get(CONF_PERSON_NAME, "") if user_input else "",
                    ): TextSelector(TextSelectorConfig()),
                    vol.Required(
                        CONF_DIET_SLUG,
                        default=user_input.get(CONF_DIET_SLUG) if user_input else vol.UNDEFINED,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=self._diet_options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return KuchniaVikingaOptionsFlow()


class KuchniaVikingaOptionsFlow(OptionsFlow):
    """Lets the user change the diet for an existing household member."""

    def __init__(self) -> None:
        # `self.config_entry` is injected by the framework before any step runs.
        self._diet_options: list[SelectOptionDict] = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if not self._diet_options:
            try:
                self._diet_options = await _fetch_diet_options(self.hass)
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Failed to fetch diet list: %s", err)
                return self.async_abort(reason="cannot_connect")
            if not self._diet_options:
                return self.async_abort(reason="no_diets_found")

        if user_input is not None:
            diet_slug = user_input.get(CONF_DIET_SLUG)
            if diet_slug in {opt["value"] for opt in self._diet_options}:
                return self.async_create_entry(
                    title="",
                    data={CONF_DIET_SLUG: diet_slug},
                )

        current = self.config_entry.options.get(
            CONF_DIET_SLUG,
            self.config_entry.data.get(CONF_DIET_SLUG),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DIET_SLUG, default=current): SelectSelector(
                        SelectSelectorConfig(
                            options=self._diet_options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )
