# Manual History/Astrology Audit 1500-1900

Data audytu: 2026-05-23

Zakres: `work/reports/pre1900_quality_audit.md/json`, wszystkie 28 dat kontrolnych dla `swiss_1500_now_global_slow_v1.npz`.

Zasada audytu: to nie jest dowodzenie, ze silnik "ma racje"; to kontrola, czy zwracane wydarzenia nie sa przypadkowe, czy nie gubia oczywistych punktow historycznych, czy long-process context nie wypycha wydarzen punktowych, i czy skonfigurowane cycle drivers sa co najmniej spojne z oczekiwaniami benchmarku.

## A. Co dziala dobrze

- Audit obejmuje sensowna siatke kontrolna: 28 przypadkow od 1501 do 1898 plus negatywny przypadek 1492 poza warstwa reliable history.
- Dla 26/28 przypadkow oczekiwane `expected_event_ids` sa obecne w top wynikach. Po ostatniej poprawce widac, ze boundary-aware ranking pomaga przypadkom startu procesu: 1543, 1618 i 1884 przestaly byc realnie gubione.
- Negatywny przypadek 1492 zachowuje sie poprawnie: API nie udaje pewnosci poza zakresem indeksu, tylko zwraca blad o braku wierszy w oknie.
- Zrodla sa technicznie stabilne: ostatni `curated_source_fragility` pokazuje 238/238 URL OK i zero high/medium risk. To jest kontrola dostepnosci, nie kontrola jakosci merytorycznej.
- Coverage 1500-1900 ma dobra baze startowa: 101 wydarzen, brak eventow bez zrodel, brak stulecia z twardym ostrzezeniem coverage.

## B. Co wyglada wiarygodnie historycznie

Przypadki, w ktorych wynik jest historycznie mocny albo wystarczajaco wiarygodny:

| Data | Wynik audytu |
| --- | --- |
| 1501 Atlantic slave trade boundary | Historycznie sensowne jako dolny brzeg reliable layer, ale to przypadek cienki: tylko jeden long process i niska pewnosc narracyjna. Nie traktowac jako jakosciowy benchmark poza sprawdzeniem granicy. |
| 1517 Protestant Reformation | Trafne. Reformation jest oczywistym wydarzeniem kontrolnym; Britannica potwierdza 1517 i Luthera/Ninety-five Theses. |
| 1543 Scientific Revolution | Trafne po poprawce rankingu. Scientific Revolution jest w top 6 mimo konkurencji wojennej i imperialnej. Rok 1543 ma mocne uzasadnienie przez Copernicusa i Vesaliusa, ale event 1543-1687 jest szerokim procesem. |
| 1582 Gregorian calendar | Trafne. Data 1582-10-15 i zwrocenie Gregorian calendar sa dobre; szeroki kontekst reformatorski jest akceptowalny. |
| 1618 Thirty Years' War opening | Trafne po poprawce. Defenestration of Prague 1618 jest prawidlowym markerem otwarcia wojny. |
| 1648 Westphalia | Trafne. Thirty Years' War i Eighty Years' War sa oczekiwane; wojenny bias jest tu naturalny. |
| 1660 Royal Society | Trafne. Royal Society jako punkt naukowo-instytucjonalny jest dobrze wydobyty. |
| 1688 Glorious Revolution | Trafne. Kontekst Enlightenment/Scientific Revolution jest szeroki, ale nie wypycha glownego eventu. |
| 1694 Bank of England | Trafne. Instytucja finansowa dobrze dziala jako punkt gospodarczy. |
| 1756 Seven Years' War | Trafne. Kontekst globalno-imperialny pasuje, choc lista jest long-process-heavy. |
| 1776 American Revolution | Trafne. Pojawia sie American Revolution; dodatkowe Pugachev/Partitions/Industrial context nie dominuje w sposob bledny. |
| 1787 United States Constitution | Trafne. Zrodlo National Archives jest bardzo dobre. |
| 1789 French Revolution | Trafne, ale ranking wymaga uwagi: French Revolution jest druga po US Constitution, a Enlightenment jest w matched, nie jako oddzielny `context_events`. |
| 1791 Haitian Revolution | Trafne. French Revolution jako sasiadujacy kontekst jest historycznie uzasadniona. |
| 1796 Smallpox vaccine | Trafne i czyste: brak warningow, event punktowy dobrze wydobyty. |
| 1814 Congress of Vienna | Trafne, ale Napoleonic Wars sa przed Congress of Vienna; to zrozumiale historycznie, bo Kongres jest rozliczeniem epoki napoleonskiej. |
| 1821 Greek War of Independence | Trafne. Kontekst industrialny i imperialny jest szeroki, ale nie gubi glownego eventu. |
| 1848 Revolutions of 1848 | Trafne. Communist Manifesto i revolutions 1848 razem sa bardzo sensowne. |
| 1859 Origin of Species | Trafne i czyste. |
| 1861 American Civil War | Trafne, choc Origin of Species jest wyzej niz wojna; historycznie to dziwny ranking dla daty Fort Sumter. |
| 1868 Meiji Restoration | Trafne, ale Austro-Prussian War jako pierwszy wynik jest rankingowo dziwne. |
| 1869 Periodic table / Suez | Trafne: oba expected eventy sa widoczne. |
| 1870 Franco-Prussian War | Trafne, ale event jest dopiero czwarty; bliskie wydarzenia 1869 konkuruja za mocno. |
| 1884 Berlin Conference / Sino-French War | Trafne po poprawce: oba expected eventy sa obecne. Berlin Conference nie jest top 1, ale jest widoczny. |
| 1895 science and imperial wars | Trafne: X-ray, First Sino-Japanese War, First Italo-Ethiopian War sa w top. |
| 1898 Spanish-American War | Trafne. |

## C. Co wyglada wiarygodnie astrologicznie

- W benchmarku skonfigurowano tylko 7 przypadkow z konkretnymi `expected_cycle_drivers`: 1517, 1648, 1756, 1789, 1848, 1868, 1895.
- Nie ma zadnych `missing_expected_cycles`, wiec technicznie cycle expectations przechodza.
- Najbardziej wiarygodne astrologicznie pary przypadkow:
  - 1648: Neptune-Pluto opposition jako marker epokowego przelomu ukladu westfalskiego.
  - 1756: Pluto-Uranus square jako marker globalnej wojny imperialnej.
  - 1848: Jupiter-Saturn trine jako cykl polityczno-spoleczny dla fali rewolucyjnej.
  - 1868: Neptune-Uranus square jako szeroki modernizacyjny/transsystemowy marker Meiji.
  - 1895: Jupiter-Saturn square jako napiecie instytucjonalno-imperialne w roku nauki i wojen regionalnych.
- Slabszy punkt: 21/28 przypadkow nie ma oczekiwanego drivera astrologicznego. Dla tych dat audit mierzy glownie retrieval/ranking historyczny, a nie jakosciowa interpretacje astrologiczna.
- Slabszy punkt: wiele odpowiedzi ma `long_process_heavy`; astrologicznie to moze sztucznie wzmacniac "epokowe" narracje kosztem ostrych wydarzen punktowych.

## D. Brakujace wazne wydarzenia

To sa braki w seedzie, nie rekomendacja masowego dodawania od razu. Priorytet powinien zalezec od tego, czy chcemy wzmacniac polityke, nauke/technologie, religie, gospodarke czy global balance.

### 1500-1600

- Peace of Augsburg, 1555 - wazny punkt prawno-religijny reformacji w Rzeszy.
- Union of Lublin, 1569 - kluczowy punkt ustrojowy Europy Srodkowo-Wschodniej.
- St. Bartholomew's Day Massacre, 1572 - wazny punkt francuskich wojen religijnych.
- Battle/Siege of Vienna, 1529 - wczesny osmansko-habsburski punkt graniczny; w seedzie jest wojna Ottoman-Safavid, ale mniej Zachodnia/centralnoeuropejska strona presji osmanskiej.
- Lepanto, 1571 - wazna morska bitwa w konflikcie osmansko-chrzescijanskim.

### 1600-1700

- Siege/Battle of Vienna, 1683 - bardzo duzy brak dla geopolityki Europy i Imperium Osmanskiego.
- English Bill of Rights, 1689 - naturalne dopelnienie Glorious Revolution.
- Qing consolidation / Kangxi high Qing marker - Ming-Qing transition jest obecny, ale dlugi; brakuje punktu stabilizacji Qing.
- Treaty of Nerchinsk, 1689 - istotne dla relacji Rosja-Qing i granic Eurazji.
- Dutch financial/stock exchange development - VOC jest obecny, ale brakuje oddzielnego kapitalowo-finansowego markeru.

### 1700-1800

- Act of Union, 1707 - wazny punkt panstwowy dla Wielkiej Brytanii.
- South Sea Bubble, 1720 - duzy marker finansowy i spekulacyjny.
- American Declaration of Independence, 1776-07-04 - American Revolution jest obecna, ale deklaracja jako punkt moze byc osobnym instant eventem.
- Bill of Rights, 1791 - wazny konstytucyjny marker USA.
- Abolitionism as organized movement, 1783/1787 - seed ma Atlantic slave trade i Haitian Revolution, ale malo antyniewolniczych instytucji.

### 1800-1900

- Louisiana Purchase, 1803 - bardzo duzy brak geopolityczny; ma tez znaczenie dla przypadku 1804.
- British/US abolition of slave trade, 1807/1808 - wazny punkt spoleczno-gospodarczy wobec obecnego long process Atlantic slave trade.
- Revolutions of 1830 / July Revolution, 1830 - brakuje dla okna, w ktorym testujemy Algeria 1830.
- Telegraph public line, 1844 - duzy brak technologiczny.
- Germ theory / antiseptic surgery, 1860s-1880s - duzy brak naukowo-medyczny.
- Emancipation of Russian serfs, 1861 - duzy brak spoleczno-polityczny.
- Italian unification / Kingdom of Italy, 1861-1871 - duzy brak panstwotworczy.
- German Empire founding, 1871-01-18 - Franco-Prussian War jest obecna, ale brakuje skutku politycznego.
- Paris Commune, 1871 - wazny punkt rewolucyjno-spoleczny.
- Telephone, 1876 - duzy brak technologiczny.
- International Meridian Conference, 1884 - wazny punkt globalnej standaryzacji czasu/geografii; szczegolnie pasuje do roku Berlin Conference, ale w innym rejestrze.

## E. Bledne lub zbyt szerokie wydarzenia

- `evt_atlantic_slave_trade` jest potrzebny, ale jego zakres 1501-1867 jest tak szeroki, ze moze zbyt latwo pojawiac sie jako tlo w bardzo wielu epizodach. To dobry context, ale slaby rankingowy konkurent dla wydarzen punktowych.
- `evt_dutch_east_india_company` 1602-1799, `evt_mughal_empire` 1526-1857, `evt_maratha_empire` 1674-1818 i `evt_enlightenment` 1685-1815 dzialaja jako duze tla. Historycznie sa sensowne, ale w top-N czasem wygladaja jak dominacja "always-on" contextu.
- `evt_scientific_revolution` 1543-1687 jest historycznie akceptowalne, ale dla 1543 trzeba uwazac: to raczej start procesu przez Copernicusa/Vesaliusa niz punktowe wydarzenie rowne wojnie czy traktatowi.
- `evt_french_conquest_algeria` 1830-1904 jest bardzo szerokie. Dla daty 1830-07-05 potrzebny jest albo osobny instant/boundary marker `Invasion/Capture of Algiers 1830`, albo mocniejsze traktowanie startu colonial-expansion.
- `evt_sokoto_caliphate` 1804-1903 jest szerokie i ma niska jakosc zrodel. Dla daty 1804 lepszy moze byc osobny marker `Sokoto Jihad begins / dan Fodio's hijra and jihad 1804`, a caliphate jako long process/context.
- `evt_berlin_conference` 1884-1885 jest poprawne, ale w roku 1884 konkuruje z `evt_scramble_for_africa`; trzeba pilnowac, zeby konferencja nie byla traktowana tylko jako zwykle tlo Scramble.

## F. Daty/okna do korekty

- 1804 Sokoto: obecny event 1804-1903 jest historycznie zasadny, ale okno testowe 1804-01-01 moze byc za arbitralne. Britannica/BlackPast/Oxford wskazuja 1804 jako poczatek dzihadu i powstania panstwa, ale konkretne wydarzenia startowe sa bardziej granularne niz roczny long process. Opcja: zostawic test roczny, lecz oczekiwac long-process boundary; lepsza opcja: dodac punktowy start.
- 1830 French conquest of Algeria: test na 1830-07-05 dobrze celuje w zdobycie Algiers, ale event 1830-1904 jest za szeroki. Opcja: dodac/rozbic `Invasion of Algiers / Capture of Algiers, 1830` jako instant event i zostawic conquest jako long colonial process.
- 1789 French Revolution: query 1789-07-14 jest OK, ale expected_context `evt_enlightenment` nie jest separowane do `context_events`. To raczej problem klasyfikacji contextu niz daty.
- 1861 American Civil War: dla 1861-04-12 expected event jest obecny, ale nie top 1. Jesli benchmark ma mierzyc "event dla daty", warto wymagac wyzszej pozycji dla `evt_american_civil_war`.
- 1868 Meiji Restoration: dla 1868-01-03 event jest obecny, ale Austro-Prussian War wygrywa ranking. To wyglada na pozostaly efekt szerokich okien i bliskich procesow wojennych.
- 1870 Franco-Prussian War: data jest poprawna, ale event nie powinien byc dopiero za periodic table/Suez/Meiji przy dokladnym query 1870-07-19.

## G. Zrodla do wymiany

Priorytetowe Wikipedia-only lub slabe zrodla pre-1900:

- `evt_sokoto_caliphate`: obecnie Wikipedia-only. Zamienic/dodac Britannica `Usman dan Fodio`, Britannica `Sokoto`, BlackPast `Sultanate of Sokoto`, Oxford Research Encyclopedia/AHR tam, gdzie dostepne.
- `evt_ethiopian_adal_war`: Wikipedia-only. Potrzebne lepsze zrodlo encyklopedyczne/akademickie.
- `evt_ottoman_safavid_war_1532`: Wikipedia-only. Potrzebne Britannica/Oxford/Cambridge lub dobre university source.
- `evt_spanish_conquest_inca`: Wikipedia-only. Potrzebne Britannica lub World History Encyclopedia.
- `evt_ming_qing_transition`: Wikipedia-only. Potrzebne Britannica/China history source.
- `evt_first_carnatic_war`: Wikipedia-only. Potrzebne Britannica/academic source.
- `evt_burmese_siamese_war_1765`: Wikipedia-only. Potrzebne lepsze regional history source.
- `evt_mahdist_war`: Wikipedia-only. Potrzebne Britannica/academic/institutional source.
- `evt_french_conquest_algeria`: ma Service historique de la Defense + Wikipedia. To jest lepsze niz Wikipedia-only, ale warto dodac Britannica `Algeria/Colonial rule` i/lub FranceArchives, bo obecne zrodlo SHD jest perspektywa militarno-francuska.

## H. Rekomendowane 5-15 konkretnych poprawek

1. Dodac zrodla nie-Wikipedia dla `evt_sokoto_caliphate` i podniesc `confidence_score` tylko jesli nowe zrodla faktycznie potwierdzaja zakres 1804-1903.
2. Rozwazyc dodanie osobnego point/boundary eventu `evt_sokoto_jihad_begins_1804` zamiast wymuszac ranking calego long process `evt_sokoto_caliphate`.
3. Dodac/rozbic `evt_invasion_capture_algiers_1830` jako instant event dla 1830-07-05, a `evt_french_conquest_algeria` zostawic jako long process.
4. Dodac Britannica `Algeria/Colonial rule` albo FranceArchives jako drugie mocne zrodlo dla `evt_french_conquest_algeria`.
5. Poprawic polityke contextu dla `evt_enlightenment`: w przypadkach takich jak 1789 powinno byc `context_events`, nie pelnoprawnym eventem konkurujacym o top list.
6. Dodac regression expectations na pozycje/ranking: 1861 Civil War, 1868 Meiji, 1870 Franco-Prussian War powinny wymagac eventu w top 3, nie tylko w top 6.
7. Dodac brakujace wydarzenie `evt_louisiana_purchase_1803` z Britannica/LOC, bo istotnie zmienia okno 1803-1804.
8. Dodac brakujace wydarzenie `evt_revolutions_1830` albo `evt_july_revolution_1830`, bo wyjasnia europejski kontekst roku, w ktorym zaczyna sie Algieria.
9. Dodac `evt_abolition_slave_trade_britain_1807` jako punktowy kontrapunkt dla zbyt szerokiego `evt_atlantic_slave_trade`.
10. Dodac `evt_telegraph_1844` i `evt_telephone_1876`, zeby XIX wiek nie byl nadmiernie wojna/imperium.
11. Dodac `evt_emancipation_serfs_russia_1861`, `evt_italian_unification_1861_1871`, `evt_german_empire_1871` jako brakujace osie panstwowo-spoleczne.
12. Dodac `evt_germ_theory_1860s_1880s` albo bardziej punktowo `evt_lister_antiseptic_surgery_1865` / `evt_koch_tb_1882`, zeby wzmocnic historie nauki/medycyny.
13. Dodac `evt_international_meridian_conference_1884` jako globalny standard-time/science-institution marker, ale nie zamiast Berlin Conference.
14. Dodac test wykrywajacy `long_process_heavy` displacement: jezeli point/boundary event istnieje w +/- 1 rok, long process nie powinien wypychac go poza top 6.
15. Dla wydarzen szerokich dodac klase `background_context` albo mocniejsza separacje broad context od matched eventow.

## I. Co dodac do regression tests

- `1804-01-01`: oczekiwac `evt_napoleonic_wars` plus albo `evt_sokoto_caliphate` po poprawie rankingu, albo nowy `evt_sokoto_jihad_begins_1804` jako point/boundary marker.
- `1830-07-05`: oczekiwac nowy `evt_invasion_capture_algiers_1830` w top 3 albo `evt_french_conquest_algeria` w top 6 po decyzji o modelu danych.
- `1789-07-14`: `evt_french_revolution` w top 3 oraz `evt_enlightenment` jako context, nie missing expected context.
- `1861-04-12`: `evt_american_civil_war` w top 3.
- `1868-01-03`: `evt_meiji_restoration` w top 3.
- `1870-07-19`: `evt_franco_prussian_war` w top 3.
- `1884-11-15`: utrzymac regression, ze `evt_berlin_conference` i `evt_sino_french_war` sa obecne; po dodaniu International Meridian Conference upewnic sie, ze nie wypycha Berlin Conference.
- Dodac test zliczajacy Wikipedia-only pre-1900 sources i failujacy, jesli przybywa nowych bez uzasadnienia.
- Dodac test coverage po kategoriach dla 1800-1900: nauka/technologia, reformy spoleczne, gospodarka, imperializm, wojny. Obecnie XIX wiek jest mocny w wojnach i imperial politics, ale za slaby technologiczno-spolecznie.

## Zrodla uzyte w audycie

- Encyclopaedia Britannica, Scientific Revolution: https://www.britannica.com/science/Scientific-Revolution
- Encyclopaedia Britannica, Defenestration of Prague 1618: https://www.britannica.com/event/Defenestration-of-Prague-1618
- Encyclopaedia Britannica, Thirty Years' War: https://www.britannica.com/event/Thirty-Years-War
- Encyclopaedia Britannica, Sokoto / Usman dan Fodio: https://www.britannica.com/place/Sokoto-Nigeria and https://www.britannica.com/biography/Usman-dan-Fodio
- BlackPast, Sultanate of Sokoto: https://www.blackpast.org/global-african-history/sultanate-sokoto-sokoto-caliphate/
- Oxford Research Encyclopedia/AHR snippets for Sokoto slavery and state formation: https://academic.oup.com/edited-volume/61663/chapter-abstract/553500140 and https://academic.oup.com/ahr/article-pdf/126/1/429/37720465/rhab135.pdf
- Encyclopaedia Britannica, Algeria colonial rule: https://www.britannica.com/place/Algeria/Colonial-rule
- FranceArchives, Gouvernement general de l'Algerie correspondence: https://francearchives.gouv.fr/fr/findingaid/1eaaaafe72a486f0c50fae857743df4f30a51161
- Memoire des hommes / Service historique de la Defense, Conquete de l'Algerie: https://www.memoiredeshommes.defense.gouv.fr/musees-collections-et-mecenat/collection-du-ministre/conquete-de-lalgerie-1830-1837
- Encyclopaedia Britannica, Berlin Conference: https://www.britannica.com/event/Berlin-West-Africa-Conference
- Stanford Encyclopedia of Philosophy, Enlightenment: https://plato.stanford.edu/entries/enlightenment/
- Royal Society, History: https://royalsociety.org/about-us/who-we-are/history/
- National Archives, Declaration of Independence and Constitution: https://www.archives.gov/founding-docs/declaration/ and https://www.archives.gov/milestone-documents/constitution
- Bank of England, History: https://www.bankofengland.co.uk/about/history
- Encyclopaedia Britannica, Industrial Revolution: https://www.britannica.com/event/Industrial-Revolution/The-first-Industrial-Revolution
- Encyclopaedia Britannica, Meiji Restoration: https://www.britannica.com/event/Meiji-Restoration
- Encyclopaedia Britannica, Telegraph / Telephone / Germ theory: https://www.britannica.com/technology/telegraph, https://www.britannica.com/technology/telephone, https://www.britannica.com/science/germ-theory
- NIST, International Meridian Conference context: https://www.nist.gov/blogs/taking-measure/everyday-time-and-atomic-time-part-4

## Plan kodowania/danych po raporcie

1. Najpierw poprawic zrodla dla `evt_sokoto_caliphate` i `evt_french_conquest_algeria`, bez zmiany rankingu.
2. Potem podjac decyzje modelowa: czy starty dlugich procesow kolonialnych/religijnych dodajemy jako osobne point/boundary events.
3. W drugiej kolejce dodac 5-8 najwazniejszych brakow, nie cala liste: Louisiana Purchase, abolition slave trade 1807, Revolutions/July Revolution 1830, telegraph 1844, Russian serf emancipation 1861, Italian/German unification, germ theory/telephone.
4. Dopiero po tych danych dodac regression tests na top 3/top 6 i ponownie uruchomic pelny pakiet kontroli wskazany w zadaniu.
