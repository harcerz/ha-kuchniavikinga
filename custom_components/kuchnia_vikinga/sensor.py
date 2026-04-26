"""Sensor platform — one sensor per household-member entry."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DIET_SLUG,
    CONF_PERSON_NAME,
    DATA_COORDINATOR,
    DOMAIN,
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
    async_add_entities([KuchniaVikingaDietSensor(coordinator, entry)])


class KuchniaVikingaDietSensor(CoordinatorEntity[KuchniaVikingaCoordinator], SensorEntity):
    """Sensor showing today's lunch for one household member's diet."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:silverware-fork-knife"
    _attr_translation_key = "today_obiad"

    def __init__(
        self,
        coordinator: KuchniaVikingaCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_obiad"
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
        diet = self._diet
        idx = self._today_index
        if diet is None or idx is None:
            return None
        meals = diet.days.get(idx, {})
        obiad = meals.get("obiad")
        if not obiad:
            return None
        text = obiad[0].description or obiad[0].label
        return text[:250] if text else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        diet = self._diet
        snap = self._snapshot
        if diet is None or snap is None:
            return {}

        attrs: dict[str, Any] = {
            "person": self._entry.data[CONF_PERSON_NAME],
            "diet_slug": diet.slug,
            "diet_name": diet.name,
            "menu_url": f"https://kuchniavikinga.pl/menu/#{diet.slug}",
        }

        today_idx = self._today_index
        if today_idx is not None and today_idx in diet.days:
            for meal_slug in MEALS:
                variants = diet.days[today_idx].get(meal_slug, [])
                attrs[f"today_{meal_slug}"] = _format_variants(variants)

        plan: dict[str, Any] = {}
        for day_idx, meals in sorted(diet.days.items()):
            day_date = snap.day_dates.get(day_idx)
            if day_date is None:
                continue
            day_entry: dict[str, Any] = {}
            for meal_slug in MEALS:
                variants = meals.get(meal_slug, [])
                if not variants:
                    continue
                day_entry[meal_slug] = [v.to_dict() for v in variants]
            plan[day_date.isoformat()] = day_entry
        attrs["plan"] = plan
        return attrs


def _format_variants(variants: list) -> str:
    if not variants:
        return ""
    parts = []
    for v in variants:
        if v.label and v.description:
            parts.append(f"{v.label}: {v.description}")
        else:
            parts.append(v.description or v.label)
    return " | ".join(p for p in parts if p)
