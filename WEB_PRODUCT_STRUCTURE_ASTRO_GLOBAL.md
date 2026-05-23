# Web Product Structure - Astro Global

Data: 2026-05-23

## Decyzja produktowa

Astro Global ma isc w kierunku publicznej strony i aplikacji webowej, ale nie jako
typowy "horoskop online". Docelowy charakter produktu:

```txt
astrological history research desk
```

To oznacza spokojny, elegancki interfejs badawczy: duzo kontekstu, zrodla, confidence,
wyjasnienie "why this match?" i jasny podzial miedzy obliczeniami astronomicznymi,
warstwa historyczna oraz narracja.

## Mapa strony

| Route | Nazwa | Rola |
| --- | --- | --- |
| `/` | Home | Szybkie pokazanie, czym jest Astro Global i wejscie do najwazniejszych trybow. |
| `/today` | Today | Codzienny klimat planetarny i najblizsze historyczne analogie. |
| `/explorer` | Explorer | Glowny tryb: wpisz date albo rok i sprawdz uklad, cykle, epoki i wydarzenia. |
| `/compare` | Compare | Porownanie dwoch dat albo epok, np. `2026 vs 1989`. |
| `/blog` | Blog | Przestrzen autorska zony: reczne teksty, interpretacje i edukacja. |
| `/articles` | Articles | Teksty generowane lub wspierane przez silnik Astro Global. |
| `/about` | About | O projekcie, intencji i granicach interpretacji. |
| `/transparency` | Transparency | Zrodla, silnik, GitHub, licencje i zasady uzycia AI. |

Menu glowne:

```txt
Home | Today | Explorer | Compare | Blog | About | Transparency
```

Footer na kazdej stronie:

```txt
Powered by Swiss Ephemeris / pyswisseph · Open-source code on GitHub
```

## Home

Pierwszy ekran ma od razu mowic:

```txt
Astro Global
Historyczny silnik rezonansow planetarnych
```

Sekcje strony glownej:

1. Dzisiejszy glowny uklad.
2. Najsilniejsze aktywne cykle.
3. Najblizsze historyczne rezonanse.
4. Ostatnie artykuly.
5. Wejscie do Explorera.

Home nie jest landing page'em marketingowym. Ma skracac droge do pracy z danymi.

## Today

`/today` to codzienna strona klimatu planetarnego. Powinna pokazywac:

- aktywne cykle,
- sile ukladu: `weak`, `moderate`, `strong`,
- rzadkosc konfiguracji,
- podobne lata,
- najwazniejsze wydarzenia historyczne,
- krotka interpretacje bez jezyka predykcyjnego.

Przykladowy ton:

```txt
Dzis aktywny jest cykl Saturn-Neptune.
Podobne uklady pojawialy sie w latach X, Y, Z.
Wtedy dominowaly motywy: transformacja struktur, kryzys idei, przebudowa instytucji.
```

Backendowo `/today` powinno byc cacheowanym/scheduled snapshotem opartym o te same
kontrakty co `/resonance/search`, a nie osobna logika w UI.

## Explorer

`/explorer` jest najwazniejsza funkcja produktu.

Uzytkownik wpisuje:

```txt
1530
1989
2026-05-23
```

Wynik:

- uklad planet,
- dominujace cykle,
- podobne epoki,
- wydarzenia historyczne,
- `score` i `confidence`,
- wyjasnienie "dlaczego ten match?",
- zrodla i ograniczenia danych.

Explorer powinien byc pierwszym pelnym UI nad obecnym backendem, bo obecne API juz ma
wiekszosc potrzebnych pol: `planetary_state`, `episodes`, `primary_cycles`,
`supporting_cycles`, `matched_events`, `context_events`, `sources`, `score_breakdown`,
`event_coverage`, `narrative_confidence` i `deterministic_summary`.

## Compare

`/compare` porownuje dwie daty albo epoki:

```txt
2026 vs 1989
1530 vs 2026
1968 vs 1848
```

Powinno pokazac:

- podobne cykle,
- roznice w ukladach,
- wspolne motywy historyczne,
- wydarzenia po obu stronach,
- confidence i zrodla,
- wyjasnienie, ktore cechy sa realnie wspolne, a ktore tylko powierzchownie podobne.

Backend gap: potrzebny bedzie deterministyczny endpoint `POST /resonance/compare`.
Nie powinien byc generowany przez LLM; model moze opisac wynik, ale porownanie musi
wyjsc z danych backendu.

## Blog

`/blog` jest przestrzenia autorska zony:

- artykuly reczne,
- interpretacje,
- kosmogramy i wpisy edukacyjne,
- wlasny styl i glos.

AI moze tworzyc szkice historyczne albo research outline, ale tresc blogowa musi miec
edytowalny workflow i wyrazne autorstwo czlowieka. To wymaga osobnego CMS/admin flow
albo prostego repo-based content workflow, zanim strona stanie sie publiczna.

## Articles

`/articles` to osobna kategoria:

```txt
Generated / Assisted by Astro Global
```

Przyklady tematow:

- Wchodzimy w uklad X - kiedy byl widoczny wczesniej?
- Uran w Gemini: historyczne analogie.
- Saturn-Neptune: motyw rozpuszczania struktur.

Kazdy artykul silnika powinien miec:

- date wygenerowania,
- uzyty zakres danych,
- event IDs i zrodla,
- oznaczenie, czy byl `generated`, `assisted` albo `editor reviewed`,
- link do powiazanej analizy w Explorerze.

## About

`/about` wyjasnia projekt prostym jezykiem:

- czym jest astrologia mundalna w tym narzedziu,
- czego Astro Global nie robi,
- dlaczego historia jest kontekstem, nie dowodem predykcyjnym,
- jak czytac confidence, rzadkosc i podobienstwo.

## Transparency

`/transparency` jest obowiazkowe przed publicznym webem.
Pierwsza statyczna wersja istnieje w `web/transparency/`; przed publicznym demo trzeba
utrzymac ja zgodnie z realnym stanem backendu, licencji i danych.

Minimalna tresc:

```txt
Astro Global uzywa Swiss Ephemeris / pyswisseph do obliczen astronomicznych.
Warstwa historyczna opiera sie na recznie kontrolowanym zbiorze wydarzen oraz zrodlach curated.
AI nie liczy planet i nie jest zrodlem faktow - opisuje wyniki wygenerowane przez backend.

Kod projektu jest publiczny:
GitHub: https://github.com/krapcys1-maker/astro-global
```

W tej sekcji trzeba tez jasno opisac:

- licencje i ograniczenia Swiss Ephemeris,
- roznice miedzy obliczeniem, interpretacja i narracja,
- ograniczenia danych historycznych,
- publiczne repo i sposob zglaszania problemow.

## UX zasady

1. Nie robic z tego horoskopu online.
2. Ton: badawczy, spokojny, elegancki, bez przepowiedni.
3. Pokazywac confidence badges i rarity jako osobne informacje.
4. Zawsze dawac "why this match?" przy epizodach.
5. Zawsze dawac zrodla przy wydarzeniach.
6. Oddzielac wydarzenia bezposrednie od `context_events`.
7. Nie chowac ograniczen danych; transparency jest czescia produktu.
8. UI ma byc cienkim klientem API, bez liczenia astrologii i rankingu historii po stronie frontend.

## Mapping do backendu

Juz istnieje:

- `GET /health`,
- `GET /today`,
- `GET /data/status`,
- `GET /sky/current`,
- `POST /sky/at-date`,
- `GET /events/window`,
- `POST /resonance/search`,
- `matched_events`,
- `context_events`,
- `sources`,
- `score_breakdown`,
- `event_coverage`,
- `narrative_confidence`,
- `deterministic_summary`,
- persistent Swiss `.npz` index,
- curated event layer z DuckDB/fallback CSV,
- backendowy snapshot `/today` z rekomendowanym requestem do `/resonance/search`.

Potrzebne przed publicznym webem:

- cache popularnych dat,
- `POST /resonance/compare`,
- content workflow dla `/blog` i `/articles`.

## Kolejnosc MVP web

1. Utrwalic ten web product spec w dokumentacji i statusie.
2. Dodac server/web migration guardrails do backendu.
3. Dodac cacheowany `/today` albo snapshot dzienny. [done: backend snapshot istnieje]
4. Zbudowac lekki web shell z trasami i wspolnym layoutem.
5. Zrobic pierwszy funkcjonalny `/explorer`.
6. Dodac `/transparency` jako statyczna strone przed publicznym demo.
7. Dopiero potem rozwijac `/compare`, `/blog` i `/articles`.

## Glowne ryzyka

- Publiczne wystawienie lokalnego API bez rate limitu i guardraili.
- Koszty i abuse przy DeepSeek/Deep Analysis.
- Swiss Ephemeris i decyzje licencyjne przy dystrybucji/komercjalizacji.
- Pomieszanie bloga autorskiego z artykulami generowanymi.
- Zbyt horoskopowy ton, ktory oslabia badawczy charakter projektu.
- Brak redakcyjnej kontroli przy tresciach publicznych.
