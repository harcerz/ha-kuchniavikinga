"""The Kuchnia Vikinga integration.

Each config entry represents one household member with one selected diet.
All entries share a single DataUpdateCoordinator that fetches the public
menu page once every 6 hours.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import KuchniaVikingaCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]


async def _get_or_create_shared_coordinator(
    hass: HomeAssistant,
) -> KuchniaVikingaCoordinator:
    """Return the shared coordinator, creating and refreshing it on first use."""
    bucket = hass.data.setdefault(DOMAIN, {})
    coordinator: KuchniaVikingaCoordinator | None = bucket.get(DATA_COORDINATOR)
    if coordinator is None:
        coordinator = KuchniaVikingaCoordinator(hass)
        bucket[DATA_COORDINATOR] = coordinator
        await coordinator.async_config_entry_first_refresh()
    return coordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one household-member entry."""
    await _get_or_create_shared_coordinator(hass)

    # Reload the entry whenever its options change (e.g. user picks a different diet)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one entry's platforms.

    The shared coordinator stays in `hass.data` deliberately: a reload of the
    last entry would otherwise drop it and force an immediate re-fetch of the
    2.8 MB menu page. The coordinator pauses its polling automatically when no
    entity listeners remain, so leaving it in place costs nothing — but if the
    user later re-adds an entry the warm snapshot is reused.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
