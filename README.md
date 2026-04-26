# ha-kuchniavikinga

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Integracja Home Assistant pobierająca menu z [kuchniavikinga.pl/menu](https://kuchniavikinga.pl/menu/) (wszystkie 17 diet, 14 dni do przodu) i udostępniająca je jako encje sensora i kalendarza — z osobnym wyborem diety na każdego domownika.

## Co dostajesz

Integrację można dodać **wielokrotnie** — raz na każdego domownika. Każdy wpis to:

- Osobne **urządzenie** w Home Assistant (nazwa = imię domownika)
- **1 sensor** — `state` = dzisiejszy obiad domownika
  - atrybuty: `today_sniadanie`, `today_drugie_sniadanie`, `today_obiad`, `today_podwieczorek`, `today_kolacja`, pełny `plan` (14 dni × posiłki), `diet_name`, `diet_slug`, `menu_url`
- **1 kalendarz** — każdy posiłek jako wydarzenie z godziną:
  - Śniadanie 8:00, Drugie śniadanie 10:30, Obiad 13:00, Podwieczorek 16:00, Kolacja 19:00

Wszystkie wpisy współdzielą jeden fetch HTML co 6 godzin (jedna sesja HTTP, jeden parser, kilkoro odbiorców).

## Dostępne diety

Lista jest pobierana dynamicznie podczas dodawania integracji (formularz pokazuje aktualnie dostępne na stronie). Obecnie:

Basic, Comfort, Supreme, Ladies Vibes, Keto Fusion, Types of Vege, Standard, Active Pro, Light, Śródziemnomorska, Low Carb & IG, Fish Low Carb & IG, Keto, Hashi Low Gluten & Lactose, Fodmap, Ekonomiczna, Ekonomiczna Wege.

## Instalacja przez HACS

1. HACS → ⋮ → **Custom repositories** → wklej `https://github.com/harcerz/ha-kuchniavikinga`, kategoria **Integration**.
2. Zainstaluj **Kuchnia Vikinga**, restart HA.
3. **Ustawienia → Urządzenia i usługi → Dodaj integrację → Kuchnia Vikinga**.
4. Wpisz imię domownika i wybierz jego dietę. Powtórz dla każdego domownika.

## Zmiana diety później

Każdy wpis ma **opcje** (przycisk *Konfiguruj* przy urządzeniu) — można w każdej chwili przełączyć dietę bez kasowania urządzenia, historia kalendarza i automatyzacje pozostają.

## Jak to działa pod spodem

Strona `https://kuchniavikinga.pl/menu/` jest renderowana po stronie serwera (WordPress) i nie udostępnia API JSON. Integracja:

1. Jeden `DataUpdateCoordinator` (singleton) pobiera HTML co 6 godzin.
2. Parser BS4 mapuje strukturę `data-day="dN"` + `<div class="kv-inner-diets-js">` → 17 diet × 14 dni × ≤5 posiłków.
3. Każdy config entry to "konsument" tego samego snapshota — selektywny widok dla wybranej diety.

Dwa warianty układu DOM-u są obsługiwane:
- **Diety wielowariantowe** (Basic / Comfort / Supreme / Ladies Vibes / Keto Fusion / Types of Vege) — kilka opcji na posiłek pod `<div class="diet-name">`.
- **Diety jednowariantowe** (pozostałe 11) — jedna `<div class="description">` na posiłek.

## Przykłady automatyzacji

```yaml
# Powiadomienie z dzisiejszym obiadem dla domownika "Mateusz"
automation:
  - alias: "Co dziś na obiad — Mateusz"
    trigger:
      - platform: time
        at: "11:30:00"
    action:
      - service: notify.mobile_app_mateusz
        data:
          title: "Obiad dziś"
          message: "{{ states('sensor.mateusz_dzisiejszy_obiad') }}"
```

```yaml
# Markdown card z planem na 7 dni
type: markdown
content: |
  ## Menu — {{ state_attr('sensor.mateusz_dzisiejszy_obiad', 'diet_name') }}
  {% set plan = state_attr('sensor.mateusz_dzisiejszy_obiad', 'plan') or {} %}
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

Integracja parsuje publicznie dostępną stronę WWW i działa w rozsądnych odstępach (domyślnie co 6 godzin). Nie jest oficjalnym produktem Kuchni Vikinga.
