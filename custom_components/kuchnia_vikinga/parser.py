"""HTML parser for the kuchniavikinga.pl menu page."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
import logging
from typing import Any

from bs4 import BeautifulSoup, Tag

from .const import MEALS, MONTH_PL_TO_NUM, WEEKDAY_SLUG_TO_ISO

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class MealVariant:
    """A single labelled option within a meal slot."""

    label: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return {"label": self.label, "description": self.description}


@dataclass(slots=True)
class Diet:
    """A single diet (e.g. Basic, Keto, Light)."""

    slug: str
    name: str
    # day_index (0..13) -> meal_slug -> list of variants
    days: dict[int, dict[str, list[MealVariant]]] = field(default_factory=dict)


@dataclass(slots=True)
class MenuSnapshot:
    """Parsed menu — full picture for all diets and days."""

    # day_index (0..13) -> ISO date
    day_dates: dict[int, date]
    # diet slug -> Diet
    diets: dict[str, Diet]

    def to_dict(self) -> dict[str, Any]:
        return {
            "day_dates": {i: d.isoformat() for i, d in self.day_dates.items()},
            "diets": {
                slug: {
                    "name": diet.name,
                    "days": {
                        i: {meal: [v.to_dict() for v in variants] for meal, variants in meals.items()}
                        for i, meals in diet.days.items()
                    },
                }
                for slug, diet in self.diets.items()
            },
        }


def _clean(text: str) -> str:
    """Collapse whitespace and trim non-breaking spaces."""
    return " ".join(text.replace("\xa0", " ").split()).strip()


def _parse_day_dates(soup: BeautifulSoup, today: date) -> dict[int, date]:
    """Extract mapping of d0..d13 -> calendar date from the day picker."""
    result: dict[int, date] = {}
    for slide in soup.select(".swiper-slide[data-slide-index]"):
        button = slide.select_one("button[data-day]")
        if button is None:
            continue
        day_attr = button.get("data-day", "")
        if not isinstance(day_attr, str) or not day_attr.startswith("d"):
            continue
        try:
            idx = int(day_attr[1:])
        except ValueError:
            continue

        number_el = button.select_one(".number")
        # second <span> inside button is the month abbreviation
        month_el = None
        spans = button.find_all("span")
        for sp in spans:
            if sp is number_el:
                continue
            txt = _clean(sp.get_text())
            if txt and len(txt) <= 4:
                month_el = sp
                break

        if number_el is None or month_el is None:
            continue
        try:
            day_num = int(_clean(number_el.get_text()))
        except ValueError:
            continue
        month_str = _clean(month_el.get_text()).lower()
        month = MONTH_PL_TO_NUM.get(month_str)
        if month is None:
            continue

        # The 14-day window starts at most a few days before "today"; pick the
        # year that lands the date close to the current date (handles year-end roll).
        window_start = today - timedelta(days=7)
        for year in (today.year - 1, today.year, today.year + 1):
            try:
                candidate = date(year, month, day_num)
            except ValueError:
                continue
            if candidate >= window_start:
                result[idx] = candidate
                break

    return result


def _parse_diet_tabs(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Return list of (slug, display_name) for all diets in the page."""
    diets: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.select('a[data-title][href^="#"]'):
        href = anchor.get("href", "")
        if not isinstance(href, str) or not href.startswith("#"):
            continue
        slug = href[1:]
        if not slug or slug in seen:
            continue
        # Only keep slugs that have a matching diet content block on the page
        if soup.select_one(f'div#{slug}.kv-inner-diets-js') is None:
            continue
        title = _clean(str(anchor.get("data-title", "")))
        if not title:
            title = slug
        seen.add(slug)
        diets.append((slug, title))
    return diets


def _parse_meal_id(meal_id: str) -> tuple[str, str] | None:
    """Parse 'Poniedzialek-sniadanie-uastozyc' -> ('Poniedzialek', 'sniadanie')."""
    parts = meal_id.split("-")
    if len(parts) < 2:
        return None
    weekday = parts[0]
    # meal slug may itself contain underscores (drugie_sniadanie) but no dashes
    meal = parts[1]
    if weekday not in WEEKDAY_SLUG_TO_ISO:
        _LOGGER.debug("Unknown weekday slug in meal id: %s", meal_id)
        return None
    if meal not in MEALS:
        _LOGGER.debug("Unknown meal slug in meal id: %s", meal_id)
        return None
    return weekday, meal


def _parse_diet_block(block: Tag, slug: str, name: str) -> Diet:
    """Parse a single <div id="<slug>" class="kv-inner-diets-js"> block."""
    diet = Diet(slug=slug, name=name)

    for day_wrap in block.select(".tab-content-wrap[data-dayid]"):
        # BeautifulSoup lowercases HTML attribute names
        day_attr = day_wrap.get("data-dayid", "")
        if not isinstance(day_attr, str) or not day_attr.startswith("d"):
            continue
        try:
            day_idx = int(day_attr[1:])
        except ValueError:
            continue

        meals: dict[str, list[MealVariant]] = {}
        for meal_div in day_wrap.select("div.tabs-content[id]"):
            meal_id = meal_div.get("id", "")
            if not isinstance(meal_id, str):
                continue
            parsed = _parse_meal_id(meal_id)
            if parsed is None:
                continue
            _weekday, meal_slug = parsed

            variants: list[MealVariant] = []
            wraps = meal_div.select(".name-desc-wrap")
            if wraps:
                # Multi-variant diet (Basic, Comfort, Supreme, Ladies Vibes, ...)
                for variant in wraps:
                    label_el = variant.select_one(".diet-name")
                    desc_el = variant.select_one(".description")
                    label = _clean(label_el.get_text()) if label_el else ""
                    description = _clean(desc_el.get_text()) if desc_el else ""
                    if not (label or description):
                        continue
                    variants.append(MealVariant(label=label, description=description))
            else:
                # Single-variant diet — only a .description directly under .diet-dec-wrap
                desc_el = meal_div.select_one(".diet-dec-wrap > .description")
                if desc_el is None:
                    desc_el = meal_div.select_one(".description")
                description = _clean(desc_el.get_text()) if desc_el else ""
                if description:
                    variants.append(MealVariant(label="", description=description))

            if variants:
                meals[meal_slug] = variants

        if meals:
            diet.days[day_idx] = meals

    return diet


def parse_menu_html(html: str, today: date) -> MenuSnapshot:
    """Parse the full /menu/ HTML page into a MenuSnapshot."""
    soup = BeautifulSoup(html, "html.parser")

    day_dates = _parse_day_dates(soup, today)
    diets: dict[str, Diet] = {}

    for slug, name in _parse_diet_tabs(soup):
        block = soup.select_one(f'div#{slug}.kv-inner-diets-js')
        if block is None:
            continue
        diet = _parse_diet_block(block, slug, name)
        if diet.days:
            diets[slug] = diet

    return MenuSnapshot(day_dates=day_dates, diets=diets)
