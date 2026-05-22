# Plan prac - Astro Global

Data opracowania: 2026-05-22  
Folder roboczy: `d:\astro Global`  
Dokumenty wejściowe: `zarys.md`, `architektura.md`  
Status GitHub: projekt ma być prowadzony w nowym publicznym repo `krapcys1-maker/astro-global`, z folderu roboczego `D:\astro Global`, na branchu roboczym `astro-global`.

## 1. Najważniejsze ustalenia

Projekt budujemy jako lokalną aplikację desktopową do eksploracji historycznych rezonansów planetarnych. Aplikacja nie jest horoskopem natalnym, nie analizuje użytkownika i nie powinna udawać predykcji przyszłości. Jej wartość to połączenie deterministycznej astronomii, kontrolowanych danych historycznych, modelu podobieństwa konfiguracji oraz narracji AI pilnowanej przez walidację.

Główna zasada architektoniczna:

```txt
Astronomia = Swiss Ephemeris / pyswisseph + nasz kod reguł
Historia   = DuckDB + curated events + Wikidata/Wikimedia enrichment
AI         = DeepSeek V4 Pro jako narrator, nie źródło faktów
UI         = Tauri 2 + React + TypeScript jako lokalny desktop
```

MVP musi najpierw udowodnić pipeline danych. UI i AI dokładamy dopiero wtedy, gdy rdzeń potrafi dla jednej daty zwrócić: aktualny układ planet, podobne epizody historyczne, dopasowane cechy, wydarzenia i deterministyczne podsumowanie.

Decyzje potwierdzone przez właściciela:

- repo docelowe: `krapcys1-maker/astro-global`,
- widoczność GitHub: publiczne repo,
- nazwa produktu: `Astro Global`,
- charakter produktu: prywatny/lokalny projekt, bez decyzji o komercyjnej dystrybucji na tym etapie,
- język UI i narracji: polski,
- AI online: DeepSeek dozwolony dla narracji.

## 2. Definicja sukcesu produktu

Uznajemy MVP za udane, gdy użytkownik może lokalnie uruchomić aplikację, zobaczyć aktualny globalny układ planet, kliknąć analizę i dostać wynik w mniej niż kilka sekund z:

- aktualnym planetary state,
- listą niezależnych epizodów historycznych, a nie duplikatów z sąsiednich dni,
- score, percentile i etykietą typu `strong`, `moderate`, `weak`, `rare`,
- konkretnymi matched features, np. "Saturn-Uranus hard aspect",
- wydarzeniami historycznymi z podanym źródłem, jakością i confidence,
- deterministycznym podsumowaniem bez języka predykcyjnego,
- opcjonalną narracją DeepSeek V4 Pro, która przechodzi walidację JSON i nie dodaje faktów spoza wejściowych eventów.

Uznajemy V1 za udane, gdy aplikacja ma działający desktop UI, stabilny lokalny backend, curated database, enrichment z Wikidata/Wikimedia, cache, testy regresji i pierwsze raporty pokrycia danych historycznych.

## 3. Niespójności i decyzje wykryte od razu

1. W dokumentach pojawia się `ASTO Global`, ale finalna nazwa produktu to `Astro Global`. W nowych plikach, UI i brandingu używamy tylko `Astro Global`.
2. Nazwa brancha `Astro global` jest niepoprawna dla Gita. Utworzyłem poprawny odpowiednik `astro-global`.
3. Nie rozwijamy starego `krapcys1-maker/astroapp`. Właściwy projekt to nowe repo `krapcys1-maker/astro-global`.
4. Dokument `zarys.md` mówi, że external ephemeris liczy także znaki, aspekty, ingresy i retrogradacje. Poprawiona architektura słusznie to rozdziela: Swiss Ephemeris liczy pozycje i prędkości, a znaki/aspekty/orby/scoring liczymy w naszym kodzie.
5. DeepSeek API key jest w `.env` jako `DEEPSEEK_API_KEY`. Sprawdziłem dostępność modeli przez API: lista zawiera `deepseek-v4-pro` i `deepseek-v4-flash`. Klucza nie wypisujemy i nie commitujemy.
6. Swiss Ephemeris ma temat licencyjny. Prywatny lokalny MVP może ruszyć, ale dystrybucja lub produkt komercyjny wymagają osobnej decyzji licencyjnej.
7. Repo GitHub jest publiczne, więc `.env`, cache, indeksy i prywatne dane muszą być bezwzględnie wykluczone z commita.

## 4. Branch i repo

Wykonane:

```txt
Repo:   krapcys1-maker/astro-global
Base:   main
Branch: astro-global
Folder: D:\astro Global
```

Kolejny krok developerski:

```bash
cd "D:\astro Global"
git fetch origin astro-global
git checkout astro-global
```

Ten folder roboczy ma być lokalnym checkoutem tego repo. Nie tworzymy dodatkowych folderów projektu.

## 5. Docelowa architektura

```txt
Tauri 2 + React + TypeScript
        |
        v
Local FastAPI sidecar on 127.0.0.1
        |
        v
SwissEphemerisProvider
        |
        v
AstroRulesEngine
        |
        v
Vectorizer global_slow_v1
        |
        v
ExactSearch + EpisodeClustering
        |
        v
DuckDB HistoricalEventLayer
        |
        v
ThemeEngine + DeterministicSummary
        |
        v
DeepSeek V4 Pro NarrativeLayer
```

W MVP nie używamy FAISS/HNSW. Dla zakresu 1500-dziś i kroku tygodniowego exact search na NumPy/DuckDB będzie prostszy, tańszy w debugowaniu i wystarczająco szybki.

## 6. Plan wdrożenia krok po kroku

### Faza 0 - uporządkowanie repo i zasad pracy

Kroki:

1. Zainicjalizować Git bezpośrednio w `D:\astro Global`.
2. Utworzyć repo `krapcys1-maker/astro-global` i branch `astro-global`.
3. Dodać dokumenty do `docs/`: `architecture.md`, `implementation_plan.md`, `astro_profile.md`, `data_sources.md`, `known_risks.md`.
4. Dodać `.env.example` bez sekretów.
5. Dodać `.gitignore` dla `.env`, `data/duckdb`, `data/cache`, `data/vectors`, build outputów i binarek sidecara.

Sukces:

- branch istnieje i jest używany,
- sekrety nie trafiają do repo,
- dokumenty są w repo,
- można odpalić podstawowe komendy projektu bez ręcznego zgadywania struktury.

### Faza 1 - kontrakty domenowe

Kroki:

1. Spisać formalny `astro_profile_id = tropical_geocentric_apparent_v1`.
2. Ustalić model czasu: UTC, Julian Day UT, kalendarz proleptyczny gregoriański wewnętrznie, BCE przez astronomical year numbering.
3. Zdefiniować modele Pydantic: `PlanetaryPosition`, `PlanetaryState`, `Aspect`, `SearchProfile`, `HistoricalEvent`, `ResonanceEpisode`, `NarrativeInput`, `NarrativeOutput`.
4. Zdefiniować zakazane frazy narracji i reguły języka.
5. Ustalić wersjonowanie: `astro_profile_id`, `vector_version`, `search_profile_id`, `event_schema_version`.

Sukces:

- test sprawdza, że UI nigdy nie pokazuje `0 CE`,
- każde API response ma wersje profili,
- DeepSeek dostaje tylko jawnie zdefiniowany JSON input,
- wszystkie endpointy mają schematy wejścia/wyjścia.

### Faza 2 - ephemeris i reguły astrologiczne

Kroki:

1. Dodać Python package layout: `services/ephemeris`, `services/astro_rules`, `services/resonance`, `services/historical`, `services/narrative`, `services/api`.
2. Zaimplementować `SwissEphemerisProvider` na `pyswisseph`.
3. Provider zwraca tylko: longitude, latitude, speed longitude, distance opcjonalnie, flags, ephemeris version.
4. Zaimplementować `angular_distance_deg`.
5. Zaimplementować signs, elements, modality.
6. Zaimplementować aspekty w naszym kodzie: conjunction, sextile, square, trine, opposition.
7. Zaimplementować retrograde jako `speed < 0`.
8. Zaimplementować ingress proximity i station proximity.

Sukces:

- `angular_distance_deg(359, 1) == 2`,
- `angular_distance_deg(10, 190) == 180`,
- provider zwraca komplet planet dla daty UTC,
- aspekty nie są liczone przez Swiss provider,
- testy jednostkowe pokrywają kąty, znaki, aspekty, retrograde i BCE mapping.

### Faza 3 - dane historyczne

Kroki:

1. Utworzyć DuckDB schema dla `historical_event`, `event_source`, `planetary_state_index`, `resonance_run`, `narrative_cache`.
2. Dodać `curated_events.csv` jako minimalną bazę startową.
3. Dodać importer CSV z walidacją dat, zakresów, kategorii i źródeł.
4. Dodać `source_quality.yaml`, `category_map.yaml`, `region_map.yaml`.
5. Dodać endpoint lub CLI `events coverage report`.
6. Zbudować pierwszy seed 1500-dziś: wojny, rewolucje, upadki państw, odkrycia, przełomy naukowe, epidemie, kryzysy gospodarcze, ruchy społeczne, reformy religijne, okresy pokoju i prosperity.

Skąd brać dane:

1. `curated_events.csv` - obowiązkowa warstwa ręczna. To jest prawda produktowa i baza testowa.
2. Wikidata Query Service - główne źródło strukturalne dla wydarzeń, dat, QID, relacji, lokalizacji i linków do artykułów.
3. Wikidata dumps - do offline buildów, gdy SPARQL będzie za wolny albo limitowany.
4. Wikimedia REST API - krótkie opisy artykułów, linki, metadata i enrichment tekstowy.
5. EventKG - opcjonalny bulk event graph; przydatny jako dodatkowy event-centric dataset, ale nie zastępuje curated layer.
6. DBpedia - opcjonalnie jako dodatkowe typy, linki i abstracty.
7. GDELT - tylko dla nowoczesnej historii/newsów, nie jako podstawa dla 1500-dziś.

Sukces:

- każdy event ma `id`, `title`, `display_date`, `start_jd/end_jd/point_jd`, `date_precision`, `category`, `geo_scope`, `importance_score`, `confidence_score` i co najmniej jedno źródło,
- eventy zakresowe są obsługiwane tak samo jak punktowe,
- system potrafi pobrać eventy dla okna dat,
- coverage report pokazuje bias regionalny i liczbę eventów,
- brak eventów bez źródła w wynikach.

### Faza 4 - vectorizer i indeks planetarny

Kroki:

1. Zaimplementować `global_slow_v1` z planetami: Jupiter, Saturn, Uranus, Neptune, Pluto.
2. Dodać `cycle_registry.yaml`, który opisuje pary planet, cykl synodyczny, tier, wagę astrologiczną i rolę w scoringu.
3. Dodać feature groups:
   - outer synodic phase,
   - major aspect channels,
   - Jupiter-Saturn cycle,
   - sign/element/modal low-weight context,
   - ingress/retrograde,
   - rare pattern flags.
4. Użyć sin/cos dla danych kątowych.
5. Normalizować każdą grupę cech osobno do `0..1`.
6. Dodać `feature_debug_json` dla debug inspectora.
7. Dodać `cycle_strength_debug_json`: które cykle są głównym driverem, które są tylko kontekstem, i czy są rzadkie.
8. Zbudować `scripts/build_planetary_index.py`.
9. Precompute MVP: 1500-01-01 do daty buildu co 7 dni.
10. Zapisać wektory do `.npy/.npz`, mapowanie do Parquet, szczegóły do DuckDB.

Sukces:

- ten sam input daje identyczny wektor,
- wektor ma stabilny `vector_version`,
- indeks buduje się z progress barem i resume,
- raw exact search działa bez UI,
- debug JSON wyjaśnia, dlaczego wynik dostał score,
- każdy wynik potrafi wskazać `primary_cycles`, `supporting_cycles`, `cycle_tier` i `rarity_years`.

### Faza 5 - wyszukiwanie rezonansów i grupowanie epizodów

Kroki:

1. Zaimplementować exact cosine/group similarity.
2. Policz score ważony grupami, nie jedną czarną skrzynką.
3. Dodać osobny `cycle_power_score`, żeby rzadkie/ciężkie cykle nie ginęły w ogólnym cosine similarity.
4. Dodać percentyle względem całego okna.
5. Dodać top K raw candidates.
6. Dodać `episode_clustering.py`: łączyć punkty, jeśli przerwa <= 45 dni.
7. Dodać `min_independent_episode_separation_days = 365`.
8. Dodać etykiety: `strong`, `moderate`, `weak`, `rare_configuration`, `insufficient_comparable_history`.
9. Dodać rozszerzanie okna: reliable -> deep -> ancient tylko jeśli user pozwoli.

Sukces:

- wynik pokazuje epizody, nie dziesięć sąsiednich dat wokół tego samego tranzytu,
- strong wymaga score, percentyla i minimalnej liczby mocnych outer features,
- wynik `strong` nie może wynikać wyłącznie z częstych cykli Jowisza albo szybkich planet,
- search potrafi uczciwie zwrócić `rare` albo `insufficient`,
- CLI smoke test zwraca 5-8 sensownych epizodów albo jasne wyjaśnienie, czemu ich nie ma.

### Faza 6 - lokalne API

Kroki:

1. FastAPI app.
2. Endpointy:
   - `GET /health`,
   - `GET /data/status`,
   - `GET /sky/current`,
   - `POST /sky/at-date`,
   - `POST /resonance/search`,
   - `GET /events/window`,
   - `POST /narrative/generate`.
3. Backend binduje tylko do `127.0.0.1`.
4. Dodać session token middleware poza `/health`.
5. CORS tylko dla lokalnego dev/Tauri origin.
6. Dodać bezpieczne logowanie: bez kluczy API, bez pełnych promptów z sekretami.

Sukces:

- `/health` działa bez tokenu,
- endpointy poza `/health` odrzucają brak tokenu,
- backend nie startuje na `0.0.0.0`,
- API przechodzi smoke test od current sky do resonance search,
- błędy są czytelne dla UI.

### Faza 7 - deterministic summary bez AI

Kroki:

1. Zaimplementować ThemeEngine bazujący na kategoriach eventów, matched features i powtarzalnych motywach.
2. Zaimplementować deterministic summary po polsku.
3. Dodać forbidden phrases checker.
4. Dodać fallback, gdy nie ma eventów albo coverage jest słaby.

Sukces:

- aplikacja daje użyteczne podsumowanie bez DeepSeek,
- tekst nie zawiera fraz typu "to się wydarzy", "planety spowodują", "pewne jest",
- każdy motyw ma supporting event IDs,
- słabe pokrycie danych jest jawnie komunikowane.

### Faza 8 - DeepSeek V4 Pro narrative layer

Kroki:

1. Dodać `DeepSeekClient` z OpenAI-compatible base URL `https://api.deepseek.com`.
2. Model domyślny: `deepseek-v4-pro`.
3. Model fallback/kosztowy: `deepseek-v4-flash`.
4. Klucz pobierać wyłącznie z `DEEPSEEK_API_KEY`.
5. Użyć strict JSON schema/Pydantic dla outputu.
6. Wymusić, że `mentioned_event_ids` i `supporting_event_ids` są podzbiorem input events.
7. Dodać retry tylko dla błędów formatowania, nie dla halucynacji faktów.
8. Cache po `input_hash`, modelu i wersji promptu.

Sukces:

- `deepseek-v4-pro` jest wykrywany przez `/models`,
- output przechodzi Pydantic validation,
- AI nie może dodać wydarzenia bez `event_id`,
- walidator odrzuca forbidden phrases,
- po dwóch nieudanych próbach używany jest deterministic fallback,
- żaden log nie zawiera `DEEPSEEK_API_KEY`.

### Faza 9 - UI i kierunek graficzny

Koncepcja wizualna: "observatory-grade history desk". Ma być immersyjnie, ale nie kiczowato okultystycznie. Interfejs powinien wyglądać jak połączenie mapy nieba, timeline'u historycznego i narzędzia analitycznego.

Założenia:

- pierwszym ekranem jest realna aplikacja, nie landing page,
- dominują dane i eksploracja, nie marketingowy hero,
- żadnych ciężkich, jednonutowych fioletowych gradientów,
- paleta: neutralne ciemne tło, jasne panele robocze, akcenty miedzi, cyjanu, czerwieni napięcia i zieleni stabilizacji,
- wizualizacje są funkcyjne: koło nieba, aspect graph, timeline epizodów, karty dopasowań, debug inspector.

Proponowany layout desktop:

```txt
Top bar:
  data/czas, profil wyszukiwania, status danych, przycisk Analyze

Left panel:
  Current Sky wheel + lista wolnych planet + najważniejsze aspekty

Center:
  Resonance map / timeline epizodów

Right panel:
  Summary, motifs, AI narrative, caveats

Bottom drawer:
  DebugInspector: matched features, score breakdown, event sources
```

Ekrany:

1. `CurrentSky` - aktualne pozycje i aspekty.
2. `ResonanceSearch` - uruchomienie i status analizy.
3. `HistoricalTimeline` - epizody i wydarzenia.
4. `ResonanceSummary` - motywy i narracja.
5. `DebugInspector` - score breakdown i źródła.
6. `PoeticMode` - opcjonalny, dopiero po działającym rdzeniu.

Sukces:

- UI da się obsłużyć bez instrukcji na ekranie,
- najważniejsze dane są widoczne w pierwszym widoku,
- tekst nie nachodzi na siebie na desktop/mobile,
- timeline i wykresy są czytelne przy 5-8 epizodach,
- DebugInspector pozwala zrozumieć, skąd wynik się wziął,
- Playwright screenshoty potwierdzają brak pustych canvasów i layoutowych kolizji.

### Faza 10 - Tauri sidecar i packaging

Kroki:

1. Dodać `apps/desktop` z Vite + React + TypeScript.
2. Dodać Tauri 2.
3. W dev uruchamiać backend osobno przez `scripts/run_backend_dev.py`.
4. Potem spakować backend PyInstallerem/Nuitką jako sidecar.
5. Dodać `externalBin` w Tauri.
6. Przekazywać port i session token do frontendu bez zapisywania sekretów.
7. Dodać health polling i ekran błędu backendu.

Sukces:

- desktop app startuje UI i lokalny backend,
- backend używa losowego portu albo jawnego portu dev,
- UI nie działa, jeśli token jest błędny,
- build Windows przechodzi lokalnie,
- instrukcja dev setup jest krótka i powtarzalna.

### Faza 11 - testy i jakość

Minimalny zestaw testów:

- unit: kąty, BCE, znaki, aspekty, retrograde,
- unit: vectorizer i normalizacja feature groups,
- unit: episode clustering,
- golden: znane konfiguracje Jupiter-Saturn, Saturn-Pluto, Saturn-Uranus, Saturn-Neptune, Uranus-Pluto,
- search: self-retrieval dla dat z indeksu,
- search: cycle family retrieval dla mocnych cykli,
- negative controls: losowe daty, przetasowane wektory, same cykle Jowisza, brak eventów,
- regression snapshots: top epizody i score dla stałych dat kontrolnych,
- integration: build small index 1900-dziś,
- integration: `/resonance/search`,
- integration: event importer,
- integration: DeepSeek validation z mockiem,
- security: bind `127.0.0.1`, token required,
- UI: screenshoty głównych ekranów.

Szczegółowy plan testów jest w `TEST_PLAN_ASTRO_GLOBAL.md`.

Sukces:

- `pytest` przechodzi,
- smoke test pipeline działa od ephemeris do summary,
- testy łapią `0 CE`,
- testy łapią AI event IDs spoza inputu,
- testy łapią duplicate episodes,
- testy łapią fałszywe `strong resonance` z częstych aktywatorów.

## 7. Cykle planetarne, rzadkość i siła

To ma znaczenie i warto to pokazać w aplikacji. Nie wolno jednak zrobić skrótu `rzadkie = zawsze silne`. Dla produktu potrzebujemy trzech osobnych miar:

```txt
rarity_years        = obiektywna długość cyklu synodycznego / częstość aspektu
archetypal_weight  = interpretacyjna waga cyklu w astrologii mundalnej
evidence_confidence = ile mamy porównywalnych epizodów historycznych w danych
```

W praktyce wynik powinien mówić użytkownikowi: "to dopasowanie jest silne, bo aktywny jest Saturn-Pluto square i Saturn-Uranus hard phase", albo "to jest rzadkie tło epokowe Neptune-Pluto, ale mamy mało powtórzeń w reliable history, więc traktujemy je jako background, nie jako samodzielny dowód".

### 7.1. Rejestr cykli MVP

Poniższe okresy są przybliżonymi średnimi cyklami synodycznymi, czyli odstępami między podobnymi układami par planet. Dla scoringu liczymy dokładne separacje z efemeryd, ale te wartości są potrzebne do UI, wag i debugowania.

| Para | Cykl ok. | Tier | Rola w aplikacji | Interpretacja mundalna roboczo |
| --- | ---: | --- | --- | --- |
| Neptune-Pluto | 494 lata | S / epochal | tło epokowe, deep/ancient only | bardzo długie przemiany cywilizacyjne, zasoby, religie, paradygmaty |
| Uranus-Neptune | 171 lat | S / epochal | tło epokowe, rzadkie markery | ideologie, utopie, technologia, zbiorowe wizje |
| Uranus-Pluto | 127 lat | S / revolutionary | bardzo silny driver, ale z małą liczbą próbek | radykalna transformacja, rewolucje, przełomy systemowe |
| Saturn-Uranus | 45 lat | A / structural shock | silny driver MVP | napięcie starych struktur i nagłej zmiany |
| Saturn-Neptune | 36 lat | A / dissolution | silny driver MVP | erozja instytucji, wiara, ideologie, rozczarowania, kryzysy sensu |
| Saturn-Pluto | 33 lata | A / compression | silny driver MVP | presja, kontrola, kryzysy struktur, odbudowa po przymusie |
| Jupiter-Saturn | 20 lat | B / social order | ważny, ale nie samodzielnie decydujący | cykl porządku społecznego, władzy, instytucji, gospodarki |
| Jupiter-Uranus | 14 lat | C / activator | kontekst i aktywator | innowacje, przełomy, przyspieszenie, bunt |
| Jupiter-Neptune | 13 lat | C / activator | kontekst i aktywator | ekspansja wizji, religii, idealizmu, baniek narracyjnych |
| Jupiter-Pluto | 12.5 roku | C / activator | kontekst i aktywator | wzrost skali, kapitał, ambicja, intensyfikacja wpływu |

### 7.2. Klasy siły cyklu

`S / epochal`:

- bardzo rzadkie,
- nie powinny być wymagane do każdego wyniku,
- jeśli są aktywne, UI pokazuje je jako "epochal background",
- scoring dostaje bonus, ale wynik musi jawnie pokazać niską lub wysoką pewność porównania historycznego.

`A / structural`:

- najlepsze drivery MVP,
- występują na tyle często, żeby mieć porównania od 1500 roku,
- mają wystarczająco duży ciężar astrologiczny, żeby tłumaczyć globalne okresy napięcia, restrukturyzacji i przemian.

`B / social order`:

- bardzo ważne, szczególnie Jupiter-Saturn,
- występuje co około 20 lat, więc sam cykl jest zbyt częsty, żeby automatycznie oznaczał "rzadki rezonans",
- ma większą wagę, gdy wspiera cykle tier A/S albo wypada w zmianie elementu/trigonu.

`C / activator`:

- częste cykle Jowisza z planetami zewnętrznymi,
- dobre do koloru interpretacyjnego i krótszych fal,
- nie mogą samodzielnie zdominować historycznego scoringu.

`Mars / fast activator`:

- Mars może być w profilu `global_slow_plus_mars_v1`,
- używamy go tylko jako timing/tension modifier,
- nie używamy go jako głównego historycznego drivera.

### 7.3. Siła aspektu w cyklu

Astrologicznie nie wszystkie fazy cyklu są równoważne. W aplikacji pokazujemy `phase_role`:

| Faza | Kąt | Waga robocza | Znaczenie w aplikacji |
| --- | ---: | ---: | --- |
| Conjunction | 0° | 1.00 | start nowego cyklu, seed, reset archetypu |
| Opposition | 180° | 0.92 | kulminacja, polaryzacja, pełna widoczność konfliktu |
| Square | 90°/270° | 0.88 | napięcie, kryzys, wymuszenie ruchu |
| Trine | 120°/240° | 0.55 | łatwy przepływ, stabilizacja, mniejsza presja eventowa |
| Sextile | 60°/300° | 0.40 | łagodne wsparcie, kontekst, nie główny driver |

Wynik "strong resonance" powinien preferować hard phases (`conjunction`, `opposition`, `square`) na cyklach tier A/S. Trine i sextile pokazujemy w UI, ale zwykle jako supporting context.

### 7.4. Jak to pokazać w aplikacji

W UI warto dodać widoczną warstwę "Cycle Drivers":

- przy każdym epizodzie chipy: `Saturn-Pluto`, `hard phase`, `33y`, `Tier A`, `primary driver`;
- osobny pasek "Cycle Power": ile wyniku pochodzi z tier S/A/B/C;
- oznaczenie rzadkości: `common`, `notable`, `rare`, `epochal`;
- oznaczenie pewności: `well-sampled`, `thin history`, `deep-history only`;
- w DebugInspector tabela: para planet, aktualny kąt, najbliższy aspekt, orb, tier, weight, score contribution;
- na timeline odróżnić kolorami: tier S jako tło epokowe, tier A jako główne markery, tier B/C jako aktywatory.

Nie polecam robić z tego ezoterycznej "mocy procentowej" bez wyjaśnienia. Lepsze są jawne etykiety: `Primary cycle`, `Supporting cycle`, `Rare background`, `Fast activator`.

### 7.5. Zmiana w scoringu

Scoring planetarny i confidence narracyjne muszą pozostać osobnymi warstwami. Ranking dopasowań ma wynikać z podobieństwa konfiguracji planetarnej, a historia ma oceniać, jak dobrze potrafimy opisać dany wynik.

```txt
planetary_resonance_score =
  0.60 * structural_similarity +
  0.25 * cycle_power_score +
  0.15 * rarity_adjusted_percentile
```

Osobno:

```txt
narrative_confidence =
  0.45 * event_coverage_score +
  0.30 * source_quality_score +
  0.25 * evidence_confidence
```

`historical_event_support` nie może wejść do `planetary_resonance_score`, bo wtedy daty lepiej opisane historycznie mogłyby dostać wyższy ranking nie z powodu podobieństwa astronomicznego, tylko z powodu biasu danych.

`cycle_power_score` liczymy z:

```txt
cycle_power_score =
  cycle_tier_weight *
  phase_weight *
  orb_closeness *
  evidence_confidence_cap
```

Startowe `cycle_tier_weight`:

```yaml
S_epochal: 1.00
A_structural: 0.85
B_social_order: 0.60
C_activator: 0.35
Mars_fast_activator: 0.20
personal_planets: 0.00
```

Ważne zabezpieczenie: `evidence_confidence_cap` ogranicza wpływ bardzo rzadkich cykli, jeżeli w danym oknie historycznym mamy za mało porównań. Dzięki temu Neptune-Pluto może być pokazany jako potężne tło, ale nie robi fałszywego wyniku "99% pewności" na podstawie jednej lub dwóch próbek.

### 7.6. Decyzja produktowa

Tak, warto to zaznaczyć w aplikacji. To zwiększy zaufanie do wyników, bo użytkownik zobaczy, czy rezonans wynika z ciężkich cykli mundalnych, czy z częstych aktywatorów. Ma to też znaczenie techniczne: bez tego częstsze układy Jowisza albo Marsa mogą generować dużo pozornie mocnych dopasowań i przykryć wolniejsze, ważniejsze cykle.

## 8. Źródła danych historycznych - rekomendacja praktyczna

Najlepszy start to model hybrydowy:

```txt
curated CSV -> DuckDB -> wyniki MVP
Wikidata SPARQL -> enrichment kontrolowany
Wikimedia REST -> opisy i linki
EventKG/DBpedia -> opcjonalne porównanie i bulk import
```

Nie polecam zaczynać od "wszystkich wydarzeń świata". To spowoduje chaos, bias i bardzo dużo sprzątania. Najpierw robimy mały, kontrolowany seed, np. 500-1500 wydarzeń globalnych od 1500 roku. Dopiero potem dokładamy automatyczny import i coverage report.

Priorytet eventów dla MVP:

1. globalne wojny i traktaty,
2. rewolucje i przewroty,
3. upadki imperiów/państw,
4. epidemie i kryzysy demograficzne,
5. przełomy naukowe i technologiczne,
6. reformy religijne i ideologiczne,
7. kryzysy gospodarcze,
8. okresy prosperity/stabilizacji,
9. ruchy społeczne i kulturowe,
10. odkrycia geograficzne i kolonialne.

Wikidata jest najlepszym głównym źródłem strukturalnym, bo ma QID, daty, relacje, linki i dane na licencji CC0. Wikipedia/Wikimedia REST nadaje się do opisów, ale teksty wymagają respektowania licencji CC BY-SA i zapisu attribution/license note.

## 9. Ryzyka

1. Licencja Swiss Ephemeris - trzeba rozstrzygnąć przed dystrybucją.
2. Jakość historii - Wikidata ma bias geograficzny i językowy, dlatego curated layer i coverage report są obowiązkowe.
3. Fałszywe korelacje - szybkie planety mogą dawać przypadkowe dopasowania; domyślnie używamy wolnych planet.
4. Halucynacje AI - DeepSeek może pisać ładnie, ale nie może być źródłem faktów.
5. BCE i kalendarze - starożytność wymaga osobnego traktowania dat, confidence i displayu.
6. Performance build indexu - pierwszy build może potrwać; potrzebne są resume i cache.
7. Packaging sidecara - Tauri + Python wymaga osobnych binarek per OS/arch.
8. Koszt API - DeepSeek V4 Pro ma dobre parametry, ale ceny i limity mogą się zmieniać; trzeba mieć fallback do deterministic summary.
9. Prywatność - eventy i aktualny state wysyłane do DeepSeek nie są sekretne, ale trzeba jasno zdecydować, czy użytkownik akceptuje zewnętrzne AI.
10. Zawyżanie znaczenia rzadkości - bardzo rzadki cykl nie zawsze daje lepszy wynik, jeśli mamy za mało porównywalnych epizodów historycznych.
11. Dominacja częstych aktywatorów - Jowisz i Mars mogą poprawić timing, ale nie powinny same robić globalnego rezonansu.

## 10. Pozostałe decyzje od Ciebie

Potwierdzone:

- właściwe repo to `krapcys1-maker/astro-global`,
- repo na GitHubie ma być publiczne,
- nazwa produktu to `Astro Global`,
- projekt jest prywatny/lokalny na tym etapie,
- UI i narracja będą po polsku,
- DeepSeek online może być używany dla narracji.

Nadal potrzebne:

1. Wybierz pierwszy target builda: Windows only na start, czy od razu Windows/macOS/Linux.
2. Jeśli masz własną listę "ważnych wydarzeń", dostarcz ją jako seed; jeśli nie, zaczniemy od curated CSV z Wikidata.
3. Potwierdź, czy chcesz w UI tryb prosty z etykietami cykli, czy od razu pełny DebugInspector z wagami, orbami i contribution score.

## 11. Kolejność pracy od teraz

Najbliższe wdrożenie powinno iść tak:

```txt
1. Przenieść plan i architekturę do repo na branch astro-global.
2. Dodać Python package + pyproject + pytest.
3. Zrobić SwissEphemerisProvider.
4. Zrobić AstroRulesEngine.
5. Zrobić vectorizer global_slow_v1.
6. Dodać cycle_registry.yaml i cycle_power_score.
7. Dodać testy: golden dates, self-retrieval, negative controls i snapshoty scoringu.
8. Zbudować indeks 1900-dziś jako szybki proof.
9. Dodać exact search i episode clustering.
10. Dodać curated_events.csv + DuckDB schema.
11. Dodać FastAPI endpoint /resonance/search.
12. Dodać deterministic summary.
13. Dopiero potem zacząć Tauri UI.
14. Na końcu dodać DeepSeek V4 Pro narrative layer.
```

Pierwszy techniczny kamień milowy:

```txt
scripts/smoke_test_pipeline.py --date now

zwraca:
- current planetary state,
- top historical episodes,
- matched features,
- eventy z curated DB,
- deterministic summary,
- JSON gotowy dla UI i DeepSeek.
```

To jest moment, w którym projekt przestaje być koncepcją i staje się działającym produktem.

## 12. Źródła techniczne sprawdzone przy planie

- DeepSeek API models: https://api-docs.deepseek.com/api/list-models
- DeepSeek V4 release/model notes: https://api-docs.deepseek.com/news/news260424
- DeepSeek pricing/model capabilities: https://api-docs.deepseek.com/quick_start/pricing/
- Wikidata Query Service manual: https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual
- Wikidata data access/dumps: https://www.wikidata.org/wiki/Wikidata:Data_access
- Wikimedia REST API: https://www.mediawiki.org/wiki/Wikimedia_REST_API
- Wikimedia research data/dumps overview: https://meta.wikimedia.org/wiki/Research:Data
- EventKG project: https://eventkg.l3s.uni-hannover.de/
- EventKG paper: https://arxiv.org/abs/1905.08794
- NASA orbital periods: https://spaceplace.nasa.gov/years-on-other-planets/en/
- Synodic period / conjunction interval table: https://en.wikipedia.org/wiki/Conjunction_(astronomy)
- Great conjunction and Jupiter-Saturn cycle: https://en.wikipedia.org/wiki/Great_conjunction
- Outer planet cycles in mundane astrology: https://cpalondon.com/books/the-outer-planets-and-their-cycle/
- Mundane astrology synodic cycle classification reference: https://leelehman.com/Conferences/2011/Astrology_of_Sustainability.pdf
