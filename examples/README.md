# Przykładowe karty Lovelace

Kolekcja gotowych kart dashboardu wykorzystujących encje stworzone przez integrację `kuchnia_vikinga`.

| Plik | Co pokazuje |
|------|-------------|
| [`tomorrow-menu.yaml`](tomorrow-menu.yaml) | Pełne menu (wszystkie posiłki) wybranego domownika na jutro |

## Konwencja

Każdy plik w tym katalogu to **pojedyncza karta Lovelace** w formacie YAML — wklejasz go w *Edytuj dashboard → Dodaj kartę → Manual*.

We wszystkich kartach pierwsza linia w bloku Jinja (`{% set s = '...' %}`) zawiera entity_id sensora — podmień na swój przed użyciem.
