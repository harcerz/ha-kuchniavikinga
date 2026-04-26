"""Constants for the Kuchnia Vikinga integration."""

from __future__ import annotations

from datetime import time

DOMAIN = "kuchnia_vikinga"

MENU_URL = "https://kuchniavikinga.pl/menu/"

DEFAULT_SCAN_INTERVAL_HOURS = 6

# Config entry data / options keys
CONF_PERSON_NAME = "person_name"
CONF_DIET_SLUG = "diet_slug"

# Singleton coordinator key under hass.data[DOMAIN]
DATA_COORDINATOR = "coordinator"

# Polish weekday slug -> isoweekday (1=Mon ... 7=Sun)
WEEKDAY_SLUG_TO_ISO = {
    "Poniedzialek": 1,
    "Wtorek": 2,
    "Sroda": 3,
    "Czwartek": 4,
    "Piatek": 5,
    "Sobota": 6,
    "Niedziela": 7,
}

# Polish month abbreviation -> month number
MONTH_PL_TO_NUM = {
    "sty": 1,
    "lut": 2,
    "mar": 3,
    "kwi": 4,
    "maj": 5,
    "cze": 6,
    "lip": 7,
    "sie": 8,
    "wrz": 9,
    "paz": 10,
    "paź": 10,
    "lis": 11,
    "gru": 12,
}

# Meal slug -> (Polish display name, suggested time of day)
MEALS: dict[str, tuple[str, time]] = {
    "sniadanie": ("Śniadanie", time(8, 0)),
    "drugie_sniadanie": ("Drugie śniadanie", time(10, 30)),
    "obiad": ("Obiad", time(13, 0)),
    "podwieczorek": ("Podwieczorek", time(16, 0)),
    "kolacja": ("Kolacja", time(19, 0)),
}

# Default duration of a meal calendar event
MEAL_DURATION_MINUTES = 30
