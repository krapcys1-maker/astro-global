# Pre-1900 Freeze UI/API Smoke

Data: 2026-05-23

Cel: krotki freeze po patchu 225 curated events. Nie dodawac kolejnych eventow na sile; sprawdzic, czy realna sciezka API/web nadal pokazuje sensowne `matched_events` i `context_events`.

## Wynik

- Web shell smoke: OK.
- Web/API E2E smoke: OK.
- Celowany `POST /resonance/search` na `swiss_1500_now_global_slow_v1.npz`: OK dla 7/7 dat.
- Brak missing expected matched/context events w kontrolowanych datach.
- Brak warningow top episode w kontrolowanych datach.

## Kontrolowane daty

| Data | Top best date | Wynik |
| --- | --- | --- |
| 1618-05-23 | 1618-05-21 | `evt_defenestration_prague_1618` i `evt_thirty_years_war` widoczne w top matched. |
| 1648-10-24 | 1648-10-19 | `evt_peace_of_westphalia`, `evt_thirty_years_war` i `evt_eighty_years_war` widoczne w wynikach. |
| 1776-07-04 | 1776-07-01 | `evt_declaration_independence_us` i `evt_american_revolution` widoczne w top matched. |
| 1789-07-14 | 1789-07-13 | `evt_french_revolution` widoczne w matched, `evt_enlightenment` widoczne w context. |
| 1804-01-01 | 1803-12-26 | `evt_sokoto_jihad_start` i `evt_napoleonic_wars` widoczne w top matched; `evt_enlightenment` jako context. |
| 1830-07-05 | 1830-07-05 | `evt_invasion_algiers_1830` top matched. |
| 1895-11-08 | 1895-11-04 | `evt_xray_discovery`, `evt_first_sino_japanese_war` i `evt_first_italo_ethiopian_war` top matched. |

## Decyzja freeze

Ten etap danych/modelu pre-1900 jest domkniety. Najblizsza praca nie powinna polegac na dodawaniu kolejnych eventow tylko dlatego, ze sa historycznie wazne. `long_process_heavy` pozostaje znanym tematem jakosci danych, ale po tym patchu jest traktowane jako dalsza kalibracja modelu danych, nie blokujacy bug rankingu.
