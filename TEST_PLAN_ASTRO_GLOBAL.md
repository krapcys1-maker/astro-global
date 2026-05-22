# Test Plan - Astro Global

Data opracowania: 2026-05-22  
Cel: zbudować zaufanie do silników, indeksu i modelu wyszukiwania bez wiary "na oko".

## 1. Zasada testowania

Nie testujemy, czy astrologia jako interpretacja jest prawdziwa. Testujemy, czy:

- ephemeris provider zwraca poprawne pozycje i prędkości,
- nasz kod poprawnie liczy kąty, znaki, aspekty, orby, retrogradacje i cykle,
- vectorizer jest deterministyczny i nie gubi danych kołowych,
- search znajduje matematycznie podobne konfiguracje,
- episode clustering nie pokazuje duplikatów tego samego tranzytu,
- scoring nie zawyża częstych aktywatorów,
- history event layer nie podaje faktów bez źródeł,
- DeepSeek nie dodaje wydarzeń spoza wejściowego JSON.

Każdy test powinien odpowiadać na pytanie: "Czy gdyby to się popsuło, użytkownik dostałby fałszywy wynik albo fałszywe zaufanie?".

## 2. Piramida testów

```txt
unit tests
  kąty, znaki, aspekty, BCE, orby, cycle registry

golden tests
  znane daty konfiguracji planetarnych i snapshoty pozycji

property/metamorphic tests
  invariants, wrap-around, monotoniczność orbów, determinism

integration tests
  ephemeris -> vector -> search -> episodes -> events -> summary

negative tests
  daty kontrolne, shuffled vectors, zbyt częste aktywatory, brak event sources

end-to-end smoke tests
  jeden JSON gotowy dla UI i DeepSeek
```

## 3. Testy astronomii

### 3.1. Kąty i dane kołowe

Obowiązkowe testy:

```txt
angular_distance_deg(359, 1) == 2
angular_distance_deg(1, 359) == 2
angular_distance_deg(10, 190) == 180
angular_distance_deg(0, 360) == 0
angular_distance_deg(45, 45) == 0
```

Testy circular encoding:

- `359°` i `1°` mają wysokie podobieństwo,
- `0°` i `180°` mają niskie podobieństwo,
- żadna cecha kątowa nie jest porównywana liniowo jako zwykła liczba stopni.

Sukces:

- wrap-around działa,
- vectorizer nie traktuje `359°` i `1°` jako odległych.

### 3.2. Znaki, elementy, modalności

Testy:

```txt
0.0° Aries
29.999° Aries
30.0° Taurus
359.999° Pisces
```

Sukces:

- granice znaków są jednoznaczne,
- ingress proximity jest stabilne przy granicach,
- znaki są liczone w naszym kodzie, nie w providerze.

### 3.3. BCE i kalendarze

Testy:

```txt
1 BCE -> astronomical year 0
2 BCE -> astronomical year -1
500 BCE -> astronomical year -499
UI never displays 0 CE
```

Sukces:

- storage może używać astronomical year numbering,
- UI pokazuje daty historycznie zrozumiale.

## 4. Golden tests dla ephemeris

Tworzymy katalog:

```txt
tests/fixtures/ephemeris_goldens/
```

Każdy fixture zapisuje:

```yaml
id: saturn_pluto_2020_conjunction
datetime_utc: "2020-01-12T16:00:00Z"
astro_profile_id: tropical_geocentric_apparent_v1
source_checked_against:
  - Swiss Ephemeris pinned output
  - second-source note, e.g. NASA/JPL Horizons or trusted ephemeris table
tolerance_deg_modern: 0.05
positions:
  Saturn:
    longitude_deg: ...
    speed_longitude_deg_per_day: ...
  Pluto:
    longitude_deg: ...
    speed_longitude_deg_per_day: ...
expected_aspects:
  - pair: [Saturn, Pluto]
    aspect: conjunction
    max_orb_deg: 0.20
```

Ważne: złote wartości pozycji generujemy raz ze spinnowaną wersją providerów i sprawdzamy drugim źródłem. Potem fixture ma wykrywać regresje, nie być odtwarzany przy każdym teście.

### 4.1. Daty startowe do golden suite

Te daty są dobrymi punktami kontrolnymi, bo obejmują różne klasy cykli:

| ID | Data | Co sprawdzamy | Oczekiwane zachowanie |
| --- | --- | --- | --- |
| `jupiter_saturn_2020` | 2020-12-21 | Jupiter-Saturn conjunction | aspekt conjunction, tier B, strong cycle but not epochal |
| `saturn_pluto_2020` | 2020-01-12 | Saturn-Pluto conjunction | tier A, hard phase, primary driver |
| `saturn_uranus_2021_a` | 2021-02-17 | Saturn-Uranus square | tier A, hard phase |
| `saturn_uranus_2021_b` | 2021-06-14 | Saturn-Uranus square | ten sam epizod/rok cyklu, nie osobny archetyp |
| `saturn_uranus_2021_c` | 2021-12-24 | Saturn-Uranus square | hard phase, clustering powinien ograniczyć duplikaty |
| `saturn_neptune_1989` | 1989-03-03 | Saturn-Neptune conjunction | tier A, conjunction |
| `uranus_pluto_1965` | 1965-10-09 | Uranus-Pluto conjunction window | tier S, epochal background |

Daty używane w testach powinny być finalnie potwierdzone przez nasz fixture builder i drugie źródło. Jeżeli źródła różnią się godziną albo datą przez definicję geocentric ecliptic longitude vs right ascension, testujemy orb i okno, nie magiczną godzinę.

Sukces:

- provider zwraca oczekiwane pary w orb tolerancji,
- aspekt wykryty przez nasz kod zgadza się z fixture,
- `cycle_tier` i `phase_role` są poprawne.

## 5. Testy AstroRulesEngine

Testy aspektów:

```txt
0° ± orb -> conjunction
60° ± orb -> sextile
90° ± orb -> square
120° ± orb -> trine
180° ± orb -> opposition
```

Testy brzegowe:

- aspekt przy przejściu przez 0°,
- orb tuż wewnątrz limitu,
- orb tuż poza limitem,
- para planet bez aspektu nie dostaje fałszywego matcha.

Testy faz cyklu:

- conjunction ma wyższy `phase_weight` niż sextile,
- square/opposition są `hard phase`,
- trine/sextile są `supporting phase`, jeśli nie są częścią większego wzorca.

Sukces:

- aspect engine nie zależy od UI ani AI,
- wynik zawiera `orb_deg`, `exact_angle_deg`, `phase_role`, `is_applying` opcjonalnie.

## 6. Testy cycle registry i cycle power

Plik:

```txt
services/resonance/cycle_registry.yaml
```

Testy:

- wszystkie pary wolnych planet mają wpis w registry,
- każda para ma `cycle_years`, `tier`, `tier_weight`, `interpretation_role`,
- `S_epochal > A_structural > B_social_order > C_activator > Mars_fast_activator`,
- Jupiter cycles nie mogą samodzielnie dać `strong resonance`,
- Mars nie jest częścią `global_slow_v1`.

Test monotoniczności:

```txt
ten sam cykl, ten sam tier:
orb 0.1° score > orb 1.0° score > orb 4.0° score > poza orbem
```

Test evidence cap:

- Neptune-Pluto dostaje wysoką wagę tła,
- ale jeśli w reliable history jest za mało niezależnych próbek, nie może sam podbić wyniku do fałszywego `strong`.

Sukces:

- UI może pokazać `primary_cycles`, `supporting_cycles`, `rare_background`,
- scoring jest czytelny i debugowalny.

## 7. Testy vectorizera

Testy deterministyczne:

- ten sam `PlanetaryState` daje identyczny wektor bajt po bajcie,
- `vector_version` zmienia się tylko świadomie,
- każda grupa cech jest normalizowana do `0..1`,
- brak `NaN`, `inf`, pustych grup.

Testy profilu:

- `global_slow_v1` zawiera tylko Jupiter, Saturn, Uranus, Neptune, Pluto,
- Moon, Mercury, Venus, Sun i Mars nie wchodzą do core vectora,
- `global_slow_plus_mars_v1` dopuszcza Marsa tylko z limitem wagi,
- `full_sky_context_v1` nie jest domyślnym profilem history search.

Testy podobieństwa:

- ten sam state ma similarity `1.0`,
- małe przesunięcie kąta daje mały spadek similarity,
- losowo przetasowany wektor nie powinien mieć wysokiego score.

Sukces:

- vectorizer nie jest czarną skrzynką,
- `feature_debug_json` wyjaśnia wkład grup.

## 8. Testy wyszukiwarki

### 8.1. Synthetic retrieval

Budujemy mini indeks z kontrolowanymi wektorami:

```txt
date_a -> vector_a
date_b -> vector_b
date_c -> vector_c
```

Testy:

- query `vector_a` zwraca `date_a` jako top 1,
- query blisko `vector_b` zwraca `date_b`,
- query losowy nie dostaje wysokiego confidence.

Sukces:

- search engine działa bez ephemeris i bez historii.

### 8.2. Self-retrieval na prawdziwym indeksie

Dla każdej daty z golden suite:

1. data musi istnieć w indeksie albo w oknie refinement,
2. query tej daty musi zwrócić epizod zawierający tę datę w top N,
3. matched features muszą zawierać oczekiwany cykl.

Przykład:

```txt
query: 2020-01-12
expected:
  top episodes include 2020-01 window
  primary_cycles include Saturn-Pluto
  phase_role = conjunction
```

Sukces:

- model umie odnaleźć konfigurację, którą sam indeksuje.

### 8.3. Cycle family retrieval

Dla query z mocnym cyklem tier A/S:

- Saturn-Pluto conjunction powinien znaleźć inne epizody Saturn-Pluto w wysokich wynikach profilu cycle-focused,
- Saturn-Uranus square powinien znaleźć inne Saturn-Uranus hard phases,
- Jupiter-Saturn conjunction może znaleźć inne Great Conjunction windows, ale nie może sam oznaczyć wyniku jako epochal.

Sukces:

- search znajduje podobieństwo strukturalne, nie tylko datę identyczną.

### 8.4. Negative controls

Testy negatywne:

- query losowej daty bez mocnych outer features nie dostaje `strong`,
- indeks z przetasowanymi datami nie przechodzi testu event support,
- same cykle Jowisza nie dają `strong`, jeśli brak tier A/S support,
- brak eventów w oknie obniża `historical_event_support`,
- wynik bez minimum niezależnych epizodów staje się `rare` albo `insufficient`.

Sukces:

- model potrafi powiedzieć "nie wiem" lub "to słabe", zamiast zawsze generować ładną narrację.

## 9. Testy episode clustering

Testy:

- punkty co 7 dni w jednym tranzycie są łączone w jeden epizod,
- przerwa <= 45 dni łączy punkty,
- przerwa > 45 dni tworzy nowy epizod,
- `best_date` to punkt z najwyższym score,
- `min_independent_episode_separation_days = 365` usuwa zbyt bliskie duplikaty.

Sukces:

- UI nie pokazuje dziesięciu kart dla jednego tranzytu,
- top results są niezależnymi odniesieniami historycznymi.

## 10. Testy danych historycznych

Testy importera:

- event punktowy,
- event zakresowy,
- event z datą roczną,
- event z datą niepewną,
- event BCE,
- event bez źródła jest odrzucony.

Testy source quality:

- każdy event w wynikach ma `event_source`,
- `confidence_score` nie może być puste,
- `display_date` istnieje zawsze,
- `start_jd/end_jd/point_jd` są spójne.

Testy coverage:

- raport pokazuje liczbę eventów,
- raport pokazuje bias regionalny,
- brak eventów daje warning, nie pustą narrację.

Sukces:

- historia nie jest dekoracją bez źródeł,
- model nie udaje pełnej wiedzy o świecie.

## 11. Testy narracji AI

Testy z mockiem DeepSeek:

- poprawny JSON przechodzi,
- JSON z brakującym polem odpada,
- `mentioned_event_ids` spoza inputu odpadają,
- forbidden phrases odpadają,
- po dwóch błędnych odpowiedziach działa deterministic fallback.

Forbidden phrases:

```txt
to się wydarzy
planety spowodują
przewidujemy
pewne jest, że
```

Sukces:

- AI nie rozszerza faktów,
- AI nie zmienia produktu w predykcję,
- aplikacja działa bez AI.

## 12. Testy end-to-end smoke

Komenda docelowa:

```bash
python scripts/smoke_test_pipeline.py --date 2020-01-12 --profile global_slow_v1
```

Oczekiwany output:

```txt
current_state: ok
primary_cycles: includes Saturn-Pluto
search: ok
episodes: ok
events: ok or coverage warning
summary: ok
narrative_input_json: valid
```

Druga komenda:

```bash
python scripts/smoke_test_pipeline.py --date now --profile global_slow_v1
```

Sukces:

- pipeline działa od ephemeris do JSON dla UI,
- wynik da się zapisać jako fixture regresyjny,
- brak danych historycznych nie wywraca pipeline'u.

## 13. Testy regresji i snapshoty

Po każdej zmianie w scoringu zapisujemy snapshot:

```txt
tests/snapshots/resonance/
  2020-01-12_global_slow_v1.json
  2020-12-21_global_slow_v1.json
  1989-03-03_global_slow_v1.json
```

Snapshot nie ma blokować świadomych zmian modelu, ale ma wymusić odpowiedź:

- dlaczego top epizody się zmieniły,
- dlaczego score się zmienił,
- czy zmiana poprawia model,
- czy zmiana tylko przypadkiem przesunęła wagi.

Sukces:

- żadna zmiana scoringu nie przechodzi po cichu.

## 14. Testy UI

Po wejściu w Tauri/React:

- screen Current Sky nie jest pusty,
- timeline mieści 5-8 epizodów,
- chipy cykli nie nachodzą na tekst,
- DebugInspector pokazuje orb, tier, weight i contribution,
- brak eventów pokazuje warning,
- narrative fallback wygląda poprawnie po polsku.

Sukces:

- UI nie ukrywa niepewności modelu,
- użytkownik widzi, skąd wynik się wziął.

## 15. Bramka jakości MVP

MVP nie jest gotowe, dopóki nie przechodzą:

```bash
pytest
python scripts/smoke_test_pipeline.py --date 2020-01-12 --profile global_slow_v1
python scripts/smoke_test_pipeline.py --date 2020-12-21 --profile global_slow_v1
python scripts/smoke_test_pipeline.py --date now --profile global_slow_v1
```

Minimalne kryteria:

- 0 błędów unit/integration,
- golden aspects w tolerancji,
- self-retrieval działa dla golden dates,
- episode clustering usuwa duplikaty,
- AI guardrails działają na mockach,
- żaden test nie wymaga prawdziwego klucza DeepSeek poza ręcznym testem integracyjnym.

## 16. Źródła kontrolne do fixture'ów

Do finalnego zatwierdzenia golden dates używamy dwóch źródeł:

1. pinned output z naszego `SwissEphemerisProvider`,
2. drugie źródło kontrolne, np. NASA/JPL Horizons albo zaufana tabela efemeryd/aspektów.

Źródła pomocnicze dla pierwszych seed dates:

- NASA orbital periods: https://spaceplace.nasa.gov/years-on-other-planets/en/
- Great conjunction / Jupiter-Saturn: https://en.wikipedia.org/wiki/Great_conjunction
- Saturn-Pluto 2020 conjunction: https://cafeastrology.com/events/saturn-conjunct-pluto/
- Saturn-Uranus 2021 square dates: https://empower-astrology.com/2021/02/15/the-saturn-uranus-square-17th-february-2021-a-seismic-shift/
- Saturn-Neptune 1989 triple conjunction reference: https://en.wikipedia.org/wiki/Triple_conjunction

Jeżeli źródła różnią się datą o dzień przez strefę, definicję aspektu albo longitude vs right ascension, test ma sprawdzać orb i okno czasowe, a nie sztywny timestamp bez kontekstu.
