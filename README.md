# ha-kuchniavikinga

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Integracja Home Assistant pobierająca pełne menu z [kuchniavikinga.pl/menu](https://kuchniavikinga.pl/menu/) (wszystkie 17 diet, 14 dni do przodu) i udostępniająca je jako encje sensora i kalendarza.

## Co dostajesz

Po skonfigurowaniu pojawi się jedno urządzenie **Kuchnia Vikinga** z:

- **17 sensorów** (po jednym na dietę: Basic, Comfort, Supreme, Ladies Vibes, Keto Fusion, Types of Vege, Standard, Active Pro, Light, Śródziemnomorska, Low Carb & IG, Fish Low Carb & IG, Keto, Hashi Low Gluten & Lactose, Fodmap, Ekonomiczna, Ekonomiczna Wege)
  - `state` = opis dzisiejszego obiadu
  - atrybuty:
    - `today_sniadanie`, `today_drugie_sniadanie`, `today_obiad`, `today_podwieczorek`, `today_kolacja`
    - `plan` – pełne 14 dni (data ISO → posiłek → lista wariantów)
    - `diet_name`, `diet_slug`, `menu_url`
- **17 kalendarzy** (po jednym na dietę) – każdy posiłek jako wydarzenie:
  - Śniadanie 8:00, Drugie śniadanie 10:30, Obiad 13:00, Podwieczorek 16:00, Kolacja 19:00
  - Tytuł = posiłek + pierwszy wariant; pełna treść w opisie wydarzenia

## Instalacja przez HACS

1. HACS → ⋮ → **Custom repositories** → wklej `https://github.com/harcerz/ha-kuchniavikinga`, kategoria **Integration**.
2. Zainstaluj **Kuchnia Vikinga**, restart HA.
3. **Ustawienia → Urządzenia i usługi → Dodaj integrację → Kuchnia Vikinga**.

## Instalacja manualna

Skopiuj katalog `custom_components/kuchnia_vikinga` do swojego `config/custom_components/`, restart HA, dodaj integrację z UI.

## Jak to działa pod spodem

Strona `https://kuchniavikinga.pl/menu/` jest renderowana po stronie serwera (WordPress) i nie udostępnia API JSON. Integracja:

1. Pobiera HTML co 6 godzin (`DataUpdateCoordinator`).
2. Parsuje strukturę `data-day="dN"` + `<div class="kv-inner-diets-js">` w `BeautifulSoup`.
3. Mapuje 14 etykiet `d0..d13` na rzeczywiste daty z pickera dni (numer + skrót miesiąca po polsku).

Dwa warianty układu DOM-u są obsługiwane:
- **Diety wielowariantowe** (Basic / Comfort / Supreme / Ladies Vibes / Keto Fusion / Types of Vege) – każdy posiłek ma kilka opcji oznaczonych `<div class="diet-name">`.
- **Diety jednowariantowe** (pozostałe 11) – jedna `<div class="description">` na posiłek.

## Przykład użycia w automatyzacji

```yaml
# Powiadomienie z dzisiejszym obiadem dla diety Comfort
automation:
  - alias: "Co dziś na obiad?"
    trigger:
      - platform: time
        at: "11:30:00"
    action:
      - service: notify.mobile_app
        data:
          title: "Obiad dziś (Comfort)"
          message: "{{ state_attr('sensor.comfort', 'today_obiad') }}"
```

```yaml
# Karta na dashboard pokazująca pełny tygodniowy plan (custom:flex-table-card lub markdown)
type: markdown
content: |
  ## Menu Comfort – 7 dni
  {% set plan = state_attr('sensor.comfort', 'plan') or {} %}
  {% for date, meals in plan.items() %}
  ### {{ date }}
  {% for meal, variants in meals.items() %}
  **{{ meal }}**:
  {% for v in variants -%}
  - {{ v.label }}{% if v.label and v.description %}: {% endif %}{{ v.description }}
  {% endfor %}
  {% endfor %}
  {% endfor %}
```

## Disclaimer

Integracja parsuje publicznie dostępną stronę WWW i działa tylko w rozsądnych odstępach (domyślnie co 6 godzin). Nie jest oficjalnym produktem Kuchni Vikinga.
