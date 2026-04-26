"""Sensor platform for Kuchnia Vikinga — one sensor per diet."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MEALS
from .coordinator import KuchniaVikingaCoordinator
from .parser import Diet, MenuSnapshot

# State will fall back to this when no obiad is available for today
STATE_NO_DATA = "unknown"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one sensor per diet found in the latest snapshot."""
    coordinator: KuchniaVikingaCoordinator = hass.data[DOMAIN][entry.entry_id]

    known: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        snapshot = coordinator.data
        if snapshot is None:
            return
        new_entities: list[KuchniaVikingaDietSensor] = []
        for slug in snapshot.diets:
            if slug in known:
                continue
            known.add(slug)
            new_entities.append(KuchniaVikingaDietSensor(coordinator, slug))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class KuchniaVikingaDietSensor(CoordinatorEntity[KuchniaVikingaCoordinator], SensorEntity):
    """Sensor representing a single diet from kuchniavikinga.pl."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:silverware-fork-knife"

    def __init__(self, coordinator: KuchniaVikingaCoordinator, diet_slug: str) -> None:
        super().__init__(coordinator)
        self._diet_slug = diet_slug
        self._attr_unique_id = f"{DOMAIN}_{diet_slug}"
        self._attr_translation_key = "diet"
        self._attr_translation_placeholders = {"diet_name": self._diet.name if self._diet else diet_slug}
        self._attr_name = self._diet.name if self._diet else diet_slug
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
    def _today_index(self) -> int | None:
        snap = self._snapshot
        if snap is None:
            return None
        today = self.coordinator.today
        for idx, day in snap.day_dates.items():
            if day == today:
                return idx
        return None

    @property
    def available(self) -> bool:
        return super().available and self._diet is not None

    @property
    def native_value(self) -> str | None:
        """State = today's obiad (lunch) — first variant's description, truncated."""
        diet = self._diet
        idx = self._today_index
        if diet is None or idx is None:
            return None
        meals = diet.days.get(idx, {})
        obiad = meals.get("obiad")
        if not obiad:
            return None
        # Take first variant; truncate to fit HA 255-char state limit
        text = obiad[0].description or obiad[0].label
        return text[:250] if text else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        diet = self._diet
        snap = self._snapshot
        if diet is None or snap is None:
            return {}

        today_idx = self._today_index
        attrs: dict[str, Any] = {
            "diet_slug": diet.slug,
            "diet_name": diet.name,
            "menu_url": f"https://kuchniavikinga.pl/menu/#{diet.slug}",
        }

        # Today's meals as flat keys
        if today_idx is not None and today_idx in diet.days:
            for meal_slug, (meal_name, _t) in MEALS.items():
                variants = diet.days[today_idx].get(meal_slug, [])
                attrs[f"today_{meal_slug}"] = _format_variants(variants)

        # Full 14-day plan as nested dict (date -> meal -> variants)
        plan: dict[str, Any] = {}
        for day_idx, meals in sorted(diet.days.items()):
            day_date = snap.day_dates.get(day_idx)
            if day_date is None:
                continue
            day_entry: dict[str, Any] = {}
            for meal_slug, (meal_name, _t) in MEALS.items():
                variants = meals.get(meal_slug, [])
                if not variants:
                    continue
                day_entry[meal_slug] = [v.to_dict() for v in variants]
            plan[day_date.isoformat()] = day_entry
        attrs["plan"] = plan
        return attrs


def _format_variants(variants: list) -> str:
    """Render variants as a single human-readable line (or '' if none)."""
    if not variants:
        return ""
    parts = []
    for v in variants:
        if v.label and v.description:
            parts.append(f"{v.label}: {v.description}")
        else:
            parts.append(v.description or v.label)
    return " | ".join(p for p in parts if p)
