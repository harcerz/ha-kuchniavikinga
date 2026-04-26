"""Calendar platform for Kuchnia Vikinga — one calendar per diet."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MEAL_DURATION_MINUTES, MEALS
from .coordinator import KuchniaVikingaCoordinator
from .parser import Diet, MenuSnapshot


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KuchniaVikingaCoordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        snapshot = coordinator.data
        if snapshot is None:
            return
        new_entities: list[KuchniaVikingaDietCalendar] = []
        for slug in snapshot.diets:
            if slug in known:
                continue
            known.add(slug)
            new_entities.append(KuchniaVikingaDietCalendar(coordinator, slug))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class KuchniaVikingaDietCalendar(
    CoordinatorEntity[KuchniaVikingaCoordinator], CalendarEntity
):
    """Calendar entity surfacing each meal of a diet as an event."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: KuchniaVikingaCoordinator, diet_slug: str) -> None:
        super().__init__(coordinator)
        self._diet_slug = diet_slug
        diet = self._diet
        self._attr_unique_id = f"{DOMAIN}_{diet_slug}_calendar"
        self._attr_name = diet.name if diet else diet_slug
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "kuchnia_vikinga")},
            name="Kuchnia Vikinga",
            manufacturer="kuchniavikinga.pl",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://kuchniavikinga.pl/menu/",
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
                summary = _summary(meal_name, variants)
                description = _description(variants)
                events.append(
                    CalendarEvent(
                        start=start,
                        end=end,
                        summary=summary,
                        description=description,
                        location=diet.name,
                        uid=f"{DOMAIN}_{diet.slug}_{day_date.isoformat()}_{meal_slug}",
                    )
                )
        events.sort(key=lambda e: e.start)
        return events

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
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
    """First variant becomes the event title (calendar UIs only show summary)."""
    first = variants[0]
    head = first.description or first.label or meal_name
    head = head[:80]
    return f"{meal_name}: {head}"


def _description(variants: list) -> str:
    """Full meal text in the event description (visible when expanded)."""
    lines: list[str] = []
    for v in variants:
        if v.label and v.description:
            lines.append(f"• {v.label}: {v.description}")
        else:
            lines.append(f"• {v.description or v.label}")
    return "\n".join(lines)
