"""Calendar platform — one calendar per household-member entry."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DIET_SLUG,
    CONF_PERSON_NAME,
    DATA_COORDINATOR,
    DOMAIN,
    MEAL_DURATION_MINUTES,
    MEALS,
)
from .coordinator import KuchniaVikingaCoordinator
from .parser import Diet, MenuSnapshot


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KuchniaVikingaCoordinator = hass.data[DOMAIN][DATA_COORDINATOR]
    async_add_entities([KuchniaVikingaDietCalendar(coordinator, entry)])


class KuchniaVikingaDietCalendar(
    CoordinatorEntity[KuchniaVikingaCoordinator], CalendarEntity
):
    """Calendar surfacing each meal of a household member's diet."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"
    _attr_translation_key = "menu"

    def __init__(
        self,
        coordinator: KuchniaVikingaCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        person_name = entry.data[CONF_PERSON_NAME]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=person_name,
            manufacturer="kuchniavikinga.pl",
            model="Menu Kuchni Vikinga",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://kuchniavikinga.pl/menu/",
        )

    @property
    def _diet_slug(self) -> str:
        return self._entry.options.get(
            CONF_DIET_SLUG, self._entry.data[CONF_DIET_SLUG]
        )

    @property
    def _snapshot(self) -> MenuSnapshot | None:
        return self.coordinator.data

    @property
    def _diet(self) -> Diet | None:
        snap = self._snapshot
        if snap is None:
            return None
        return snap.diets.get(self._diet_slug)

    @property
    def available(self) -> bool:
        return super().available and self._diet is not None

    def _all_events(self) -> list[CalendarEvent]:
        diet = self._diet
        snap = self._snapshot
        if diet is None or snap is None:
            return []

        tz = dt_util.get_default_time_zone()
        events: list[CalendarEvent] = []
        for day_idx, meals in diet.days.items():
            day_date = snap.day_dates.get(day_idx)
            if day_date is None:
                continue
            for meal_slug, (meal_name, meal_time) in MEALS.items():
                variants = meals.get(meal_slug)
                if not variants:
                    continue
                start = datetime.combine(day_date, meal_time).replace(tzinfo=tz)
                end = start + timedelta(minutes=MEAL_DURATION_MINUTES)
                events.append(
                    CalendarEvent(
                        start=start,
                        end=end,
                        summary=_summary(meal_name, variants),
                        description=_description(variants),
                        location=diet.name,
                        uid=(
                            f"{DOMAIN}_{self._entry.entry_id}_"
                            f"{day_date.isoformat()}_{meal_slug}"
                        ),
                    )
                )
        events.sort(key=lambda e: e.start)
        return events

    @property
    def event(self) -> CalendarEvent | None:
        now = dt_util.now()
        for ev in self._all_events():
            if ev.end >= now:
                return ev
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        return [
            ev
            for ev in self._all_events()
            if ev.end >= start_date and ev.start <= end_date
        ]


def _summary(meal_name: str, variants: list) -> str:
    first = variants[0]
    head = first.description or first.label or meal_name
    return f"{meal_name}: {head[:80]}"


def _description(variants: list) -> str:
    lines: list[str] = []
    for v in variants:
        if v.label and v.description:
            lines.append(f"• {v.label}: {v.description}")
        else:
            lines.append(f"• {v.description or v.label}")
    return "\n".join(lines)
