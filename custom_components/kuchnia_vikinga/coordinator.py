"""Data update coordinator for Kuchnia Vikinga."""

from __future__ import annotations

from datetime import date, timedelta
import logging

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DEFAULT_SCAN_INTERVAL_HOURS, DOMAIN, MENU_URL
from .parser import MenuSnapshot, parse_menu_html

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=60)
USER_AGENT = (
    "Mozilla/5.0 (compatible; HomeAssistant-KuchniaVikinga/0.1; "
    "+https://github.com/harcerz/ha-kuchniavikinga)"
)


class KuchniaVikingaCoordinator(DataUpdateCoordinator[MenuSnapshot]):
    """Fetches and parses the kuchniavikinga.pl menu page."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=DEFAULT_SCAN_INTERVAL_HOURS),
        )

    async def _async_update_data(self) -> MenuSnapshot:
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                MENU_URL,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
            ) as resp:
                resp.raise_for_status()
                html = await resp.text()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching menu: {err}") from err

        today = dt_util.now().date()
        try:
            return await self.hass.async_add_executor_job(parse_menu_html, html, today)
        except Exception as err:  # noqa: BLE001 - parser failures shouldn't kill HA
            raise UpdateFailed(f"Error parsing menu HTML: {err}") from err

    @property
    def today(self) -> date:
        return dt_util.now().date()
