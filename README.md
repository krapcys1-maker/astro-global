# Astro Global

Astro Global to lokalna aplikacja desktopowa do eksploracji historycznych rezonansów planetarnych. System porównuje aktualną globalną konfigurację planet z podobnymi układami z historii, łączy je z kontrolowaną bazą wydarzeń i generuje polską narrację interpretacyjną.

Projekt nie jest horoskopem natalnym, nie analizuje użytkownika i nie jest modelem predykcyjnym. To narzędzie do symbolicznej, historycznej eksploracji cykli.

## Zasady Pracy

1. Najpierw działa pipeline, potem UI, a AI na końcu.
2. Astronomia jest deterministyczna: pozycje i prędkości liczy Swiss Ephemeris / pyswisseph, a aspekty, orby, scoring i cykle liczymy w naszym kodzie.
3. Historia pochodzi z kontrolowanych danych: curated CSV + DuckDB, potem Wikidata/Wikimedia jako enrichment.
4. DeepSeek V4 Pro jest narratorem, nie źródłem faktów.
5. Każdy fakt historyczny w narracji musi mieć `event_id` i źródło.
6. Szybkie planety nie mogą dominować globalnego scoringu historycznego.
7. Rzadkość cyklu, waga astrologiczna i pewność historyczna są osobnymi miarami.
8. Repo jest publiczne, więc nie commitujemy `.env`, kluczy API, cache, indeksów ani prywatnych danych.
9. UI i narracja są po polsku.
10. Każdy etap kończy się testem lub smoke testem, nie samym opisem.
11. Nie ufamy modelowi w ciemno: każdy silnik ma golden tests, negative controls albo snapshot regresyjny.

## Definicja Sukcesu MVP

MVP uznajemy za udane, gdy lokalnie działa przepływ:

```txt
current sky
  -> planetary state
  -> vector global_slow_v1
  -> exact historical search
  -> episode clustering
  -> curated historical events
  -> deterministic Polish summary
  -> optional DeepSeek narrative with validation
```

Minimalny wynik z `/resonance/search` musi zawierać:

- aktualny stan planetarny,
- niezależne epizody historyczne, nie duplikaty sąsiednich dni,
- `score`, `percentile`, `label` i `window_tag`,
- główne cykle: `primary_cycles`, `supporting_cycles`, `cycle_tier`,
- matched features z orbami i wkładem do wyniku,
- wydarzenia historyczne ze źródłem i confidence,
- podsumowanie bez języka predykcyjnego.

## Czego Nie Robimy W MVP

- Nie budujemy własnego silnika orbit.
- Nie zaczynamy od Tauri UI przed działającym backendem.
- Nie używamy FAISS/HNSW, dopóki exact search wystarcza.
- Nie pozwalamy AI wymyślać faktów.
- Nie traktujemy `rare` jako automatycznie `strong`.
- Nie pokazujemy `0 CE`; BCE obsługujemy przez astronomical year numbering wewnętrznie i historyczny display w UI.

## Główne Etapy

1. Dokumentacja i kontrakty domenowe.
2. Python package, `pyproject.toml`, `pytest`.
3. SwissEphemerisProvider.
4. AstroRulesEngine: kąty, znaki, aspekty, ingress, retrograde.
5. `cycle_registry.yaml` i `cycle_power_score`.
6. Vectorizer `global_slow_v1`.
7. Indeks 1900-dziś jako szybki proof, potem 1500-dziś.
8. Exact search i episode clustering.
9. DuckDB + curated historical events.
10. FastAPI local sidecar.
11. Deterministic summary po polsku.
12. DeepSeek V4 Pro narrative layer.
13. Tauri 2 + React UI.

## Pliki Projektowe

- `PLAN_PRAC_ASTRO_GLOBAL.md` - szczegółowy plan wdrożenia.
- `TEST_PLAN_ASTRO_GLOBAL.md` - testy silników, wyszukiwarki, scoringu i guardraili.
- `STATUS.md` - bieżący status, decyzje i postępy prac.
- `architektura.md` - bazowa architektura techniczna.
- `zarys.md` - pierwotny opis produktu.

## Bramka Jakości

MVP nie jest uznane za gotowe, dopóki nie przechodzą:

```bash
pytest
python scripts/smoke_test_pipeline.py --date 2020-01-12 --profile global_slow_v1
python scripts/smoke_test_pipeline.py --date 2020-12-21 --profile global_slow_v1
python scripts/smoke_test_pipeline.py --date now --profile global_slow_v1
```

Testy mają potwierdzić nie tylko happy path, ale też przypadki negatywne: brak mocnych cykli, zbyt częste aktywatory, brak eventów, halucynacje AI i duplikaty tego samego tranzytu.

## Decyzje Potwierdzone

- Repo: `krapcys1-maker/astro-global`
- Branch roboczy: `astro-global`
- Nazwa produktu: `Astro Global`
- Widoczność GitHub: publiczne repo
- Charakter produktu: prywatny/lokalny projekt na tym etapie
- Język UI i narracji: polski
- AI: DeepSeek online dozwolony dla narracji

## Aktualny Status

Bieżący stan prac zapisujemy w `STATUS.md`. Ten plik powinien być aktualizowany po każdym większym kroku, szczególnie po zmianach architektury, implementacji modułów, testach i decyzjach produktowych.
