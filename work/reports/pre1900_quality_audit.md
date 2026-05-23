# Pre-1900 Quality Audit

- Profile: `global_slow_v1`
- Index: `swiss_1500_now_global_slow_v1.npz`
- Cases: 28
- Negative cases: 1
- Regression cases: 8
- Regression failures: 0
- Missing expected event cases: 0
- Missing expected cycle cases: 0
- Top episode missing expected event cases: 0
- Warning counts: `{"index_coverage_not_full": 5, "long_process_heavy": 21, "low_confidence": 2, "low_event_coverage": 2, "thin_history": 2, "war_bias": 8}`
- Event-mix warning counts: `{"long_process_heavy": 42}`

## Findings To Review

- No missing expected events in the configured top-N audit.

## Negative Cases

### 1492-01-01 - pre reliable-history request

- Status: `passed`
- Response: `400`
- Detail: `Index has no rows inside request window.`

## Cases

### 1501-01-01 - Atlantic slave trade reliable-start boundary

- Regression: `passed`
- Coverage: `partial`
- Warnings: `index_coverage_not_full, long_process_heavy, low_confidence, low_event_coverage, thin_history`
- Expected events: `evt_atlantic_slave_trade`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: needs_review: confidence or coverage is weak
- Root-cause review: none

#### Top Episodes

1. `1500-12-31` period `1500-01-01..1500-12-31`
   - matched: `evt_atlantic_slave_trade`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `low_event_coverage, thin_history`

### 1517-01-01 - Protestant Reformation

- Regression: `passed`
- Coverage: `partial`
- Warnings: `index_coverage_not_full, long_process_heavy, low_confidence, low_event_coverage, thin_history`
- Expected events: `evt_protestant_reformation`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `Jupiter-Saturn trine B_`
- Missing expected cycles: `none`
- Manual audit: needs_review: confidence or coverage is weak
- Root-cause review: none

#### Top Episodes

1. `1517-01-01` period `1515-07-26..1517-01-01`
   - matched: `evt_protestant_reformation, evt_atlantic_slave_trade`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `low_event_coverage`
2. `1514-12-28` period `1514-11-09..1514-12-28`
   - matched: `evt_atlantic_slave_trade`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `low_event_coverage, thin_history`

### 1543-01-01 - Scientific Revolution

- Regression: `passed`
- Coverage: `partial`
- Warnings: `index_coverage_not_full, long_process_heavy, war_bias`
- Expected events: `evt_scientific_revolution`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: Fixed: event existed but was ranked behind already-running long background; boundary-aware long-process sorting now surfaces it.

#### Top Episodes

1. `1542-12-28` period `1541-10-06..1542-12-28`
   - matched: `evt_ethiopian_adal_war, evt_ottoman_safavid_war_1532, evt_protestant_reformation, evt_scientific_revolution, evt_mughal_empire, evt_atlantic_slave_trade`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
2. `1540-12-30` period `1540-12-02..1541-03-10`
   - matched: `evt_ethiopian_adal_war, evt_ottoman_safavid_war_1532, evt_protestant_reformation, evt_mughal_empire, evt_atlantic_slave_trade, evt_spanish_conquest_inca`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `war_bias`
3. `1539-12-25` period `1539-12-25..1539-12-25`
   - matched: `evt_ethiopian_adal_war, evt_ottoman_safavid_war_1532, evt_protestant_reformation, evt_mughal_empire, evt_atlantic_slave_trade, evt_spanish_conquest_inca`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `war_bias`

### 1582-10-15 - Gregorian calendar introduction

- Regression: `passed`
- Coverage: `partial`
- Warnings: `index_coverage_not_full, long_process_heavy`
- Expected events: `evt_gregorian_calendar`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1582-10-11` period `1581-03-30..1582-10-11`
   - matched: `evt_gregorian_calendar, evt_protestant_reformation, evt_eighty_years_war, evt_scientific_revolution, evt_mughal_empire, evt_atlantic_slave_trade`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
2. `1580-09-22` period `1580-09-08..1580-09-29`
   - matched: `evt_protestant_reformation, evt_eighty_years_war, evt_scientific_revolution, evt_mughal_empire, evt_atlantic_slave_trade`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1618-05-23 - Thirty Years' War opening

- Regression: `passed`
- Coverage: `partial`
- Warnings: `index_coverage_not_full, long_process_heavy`
- Expected events: `evt_defenestration_prague_1618, evt_thirty_years_war`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: Fixed: event existed but its start boundary was penalized against older ongoing processes in the episode window.

#### Top Episodes

1. `1618-05-21` period `1617-01-09..1618-05-21`
   - matched: `evt_defenestration_prague_1618, evt_thirty_years_war, evt_protestant_reformation, evt_ming_qing_transition, evt_tokugawa_shogunate, evt_dutch_east_india_company`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
2. `1616-05-16` period `1616-04-04..1616-06-06`
   - matched: `evt_protestant_reformation, evt_tokugawa_shogunate, evt_dutch_east_india_company, evt_eighty_years_war, evt_scientific_revolution, evt_mughal_empire`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1648-10-24 - Peace of Westphalia / 1648 settlement

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy, war_bias`
- Expected events: `evt_peace_of_westphalia, evt_thirty_years_war, evt_eighty_years_war`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `Neptune-Pluto opposition S_`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1648-10-19` period `1647-08-12..1648-10-19`
   - matched: `evt_peace_of_westphalia, evt_english_civil_war, evt_thirty_years_war, evt_protestant_reformation, evt_eighty_years_war, evt_ming_qing_transition`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `war_bias`
2. `1646-09-24` period `1646-09-10..1647-02-18`
   - matched: `evt_peace_of_westphalia, evt_english_civil_war, evt_thirty_years_war, evt_protestant_reformation, evt_eighty_years_war, evt_ming_qing_transition`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `war_bias`

### 1660-11-28 - Royal Society founding

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy`
- Expected events: `evt_royal_society_founding`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1660-11-22` period `1659-09-08..1660-11-22`
   - matched: `evt_royal_society_founding, evt_ming_qing_transition, evt_scientific_revolution, evt_tokugawa_shogunate, evt_dutch_east_india_company, evt_mughal_empire`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
2. `1658-11-18` period `1658-10-07..1659-02-03`
   - matched: `evt_royal_society_founding, evt_ming_qing_transition, evt_scientific_revolution, evt_tokugawa_shogunate, evt_dutch_east_india_company, evt_mughal_empire`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1688-11-05 - Glorious Revolution

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy`
- Expected events: `evt_glorious_revolution`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1688-11-01` period `1688-06-28..1688-11-01`
   - matched: `evt_glorious_revolution, evt_scientific_revolution, evt_maratha_empire, evt_tokugawa_shogunate, evt_dutch_east_india_company, evt_mughal_empire`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
2. `1686-11-04` period `1686-10-21..1687-03-31`
   - matched: `evt_glorious_revolution, evt_scientific_revolution, evt_maratha_empire, evt_tokugawa_shogunate, evt_dutch_east_india_company, evt_mughal_empire`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1694-07-27 - Bank of England founding

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy`
- Expected events: `evt_bank_of_england_founding`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1694-07-26` period `1693-05-11..1694-07-26`
   - matched: `evt_bank_of_england_founding, evt_maratha_empire, evt_tokugawa_shogunate, evt_dutch_east_india_company, evt_mughal_empire, evt_atlantic_slave_trade`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
2. `1692-07-28` period `1692-06-02..1692-10-27`
   - matched: `evt_maratha_empire, evt_tokugawa_shogunate, evt_dutch_east_india_company, evt_mughal_empire, evt_atlantic_slave_trade`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1756-05-17 - Seven Years' War

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy`
- Expected events: `evt_seven_years_war`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `Pluto-Uranus square S_`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1756-05-17` period `1756-02-02..1756-05-17`
   - matched: `evt_seven_years_war, evt_dutch_east_india_company, evt_maratha_empire, evt_mughal_empire, evt_atlantic_slave_trade, evt_tokugawa_shogunate`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
2. `1755-04-28` period `1755-03-10..1755-12-01`
   - matched: `evt_seven_years_war, evt_dutch_east_india_company, evt_maratha_empire, evt_mughal_empire, evt_atlantic_slave_trade, evt_tokugawa_shogunate`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
3. `1754-04-22` period `1754-04-15..1754-05-20`
   - matched: `evt_dutch_east_india_company, evt_maratha_empire, evt_mughal_empire, evt_atlantic_slave_trade, evt_tokugawa_shogunate, evt_encyclopedie_publication`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1776-07-04 - American Revolution

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy`
- Expected events: `evt_declaration_independence_us, evt_american_revolution`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1776-07-01` period `1775-04-17..1776-07-01`
   - matched: `evt_declaration_independence_us, evt_american_revolution, evt_pugachev_rebellion, evt_partitions_poland, evt_industrial_revolution, evt_dutch_east_india_company`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `none`
2. `1774-08-15` period `1774-05-30..1774-10-03`
   - matched: `evt_american_revolution, evt_pugachev_rebellion, evt_partitions_poland, evt_industrial_revolution, evt_dutch_east_india_company, evt_maratha_empire`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1787-09-17 - United States Constitution

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy`
- Expected events: `evt_us_constitution`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1787-09-17` period `1786-05-01..1787-09-17`
   - matched: `evt_us_constitution, evt_partitions_poland, evt_industrial_revolution, evt_dutch_east_india_company, evt_maratha_empire, evt_mughal_empire`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
2. `1785-07-25` period `1785-05-30..1785-09-26`
   - matched: `evt_partitions_poland, evt_industrial_revolution, evt_dutch_east_india_company, evt_maratha_empire, evt_mughal_empire, evt_atlantic_slave_trade`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1789-07-14 - French Revolution

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy`
- Expected events: `evt_french_revolution`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `evt_enlightenment`
- Missing expected context events: `none`
- Expected cycles: `Jupiter-Uranus conjunction C_`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1789-07-13` period `1788-04-21..1789-07-13`
   - matched: `evt_us_constitution, evt_french_revolution, evt_partitions_poland, evt_industrial_revolution, evt_dutch_east_india_company, evt_maratha_empire`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
2. `1787-08-13` period `1787-05-28..1787-10-22`
   - matched: `evt_us_constitution, evt_partitions_poland, evt_industrial_revolution, evt_dutch_east_india_company, evt_maratha_empire, evt_mughal_empire`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1791-08-22 - Haitian Revolution

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy`
- Expected events: `evt_haitian_revolution`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1791-08-22` period `1790-05-24..1791-08-22`
   - matched: `evt_french_revolution, evt_haitian_revolution, evt_partitions_poland, evt_industrial_revolution, evt_dutch_east_india_company, evt_maratha_empire`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
2. `1789-10-26` period `1789-07-13..1789-12-07`
   - matched: `evt_french_revolution, evt_partitions_poland, evt_industrial_revolution, evt_dutch_east_india_company, evt_maratha_empire, evt_mughal_empire`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
3. `1788-09-22` period `1788-09-22..1788-10-13`
   - matched: `evt_us_constitution, evt_french_revolution, evt_partitions_poland, evt_industrial_revolution, evt_dutch_east_india_company, evt_maratha_empire`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1796-05-14 - Smallpox vaccine

- Regression: `passed`
- Coverage: `full`
- Warnings: `none`
- Expected events: `evt_smallpox_vaccine`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1796-05-09` period `1794-11-24..1796-05-09`
   - matched: `evt_smallpox_vaccine, evt_french_revolution, evt_haitian_revolution, evt_white_lotus_rebellion, evt_partitions_poland, evt_industrial_revolution`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `none`
2. `1794-05-05` period `1794-04-07..1794-05-26`
   - matched: `evt_french_revolution, evt_haitian_revolution, evt_white_lotus_rebellion, evt_partitions_poland, evt_industrial_revolution, evt_dutch_east_india_company`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `none`

### 1804-01-01 - Napoleonic Wars / Sokoto boundary

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy`
- Expected events: `evt_napoleonic_wars, evt_sokoto_jihad_start`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: Fixed by data model: keep evt_sokoto_caliphate as broad long_process/context, and use evt_sokoto_jihad_start as the 1804 point/start marker.

#### Top Episodes

1. `1803-12-26` period `1802-08-30..1803-12-26`
   - matched: `evt_sokoto_jihad_start, evt_napoleonic_wars, evt_haitian_revolution, evt_white_lotus_rebellion, evt_industrial_revolution, evt_maratha_empire`
   - context: `evt_enlightenment`
   - event mix warnings: `none`
   - episode warnings: `none`
2. `1801-12-14` period `1801-11-09..1801-12-14`
   - matched: `evt_haitian_revolution, evt_white_lotus_rebellion, evt_industrial_revolution, evt_maratha_empire, evt_mughal_empire, evt_atlantic_slave_trade`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
3. `1800-11-17` period `1800-11-17..1800-11-17`
   - matched: `evt_french_revolution, evt_haitian_revolution, evt_white_lotus_rebellion, evt_industrial_revolution, evt_dutch_east_india_company, evt_maratha_empire`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1814-09-18 - Congress of Vienna

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy, war_bias`
- Expected events: `evt_congress_of_vienna`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1814-09-12` period `1814-05-16..1814-09-12`
   - matched: `evt_napoleonic_wars, evt_war_1812, evt_congress_of_vienna, evt_industrial_revolution, evt_maratha_empire, evt_spanish_american_wars_independence`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `war_bias`
2. `1812-10-19` period `1812-08-03..1812-11-30`
   - matched: `evt_napoleonic_wars, evt_war_1812, evt_industrial_revolution, evt_spanish_american_wars_independence, evt_maratha_empire, evt_mughal_empire`
   - context: `evt_enlightenment`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `war_bias`

### 1821-03-25 - Greek War of Independence

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy`
- Expected events: `evt_greek_war_independence`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1821-03-19` period `1819-12-13..1821-03-19`
   - matched: `evt_greek_war_independence, evt_industrial_revolution, evt_maratha_empire, evt_spanish_american_wars_independence, evt_mughal_empire, evt_atlantic_slave_trade`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
2. `1819-03-15` period `1819-02-15..1819-05-03`
   - matched: `evt_industrial_revolution, evt_maratha_empire, evt_spanish_american_wars_independence, evt_mughal_empire, evt_atlantic_slave_trade, evt_tokugawa_shogunate`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1830-07-05 - French conquest of Algeria

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy, war_bias`
- Expected events: `evt_invasion_algiers_1830`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: Fixed by data model: keep evt_french_conquest_algeria as broad long_process/context, and use evt_invasion_algiers_1830 as the 1830 point/start marker.

#### Top Episodes

1. `1830-07-05` period `1829-01-26..1830-07-05`
   - matched: `evt_invasion_algiers_1830, evt_greek_war_independence, evt_java_war, evt_industrial_revolution, evt_spanish_american_wars_independence, evt_mughal_empire`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `war_bias`
2. `1828-06-09` period `1828-05-19..1828-06-16`
   - matched: `evt_greek_war_independence, evt_java_war, evt_industrial_revolution, evt_spanish_american_wars_independence, evt_mughal_empire, evt_atlantic_slave_trade`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `war_bias`

### 1848-02-24 - Revolutions of 1848

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy`
- Expected events: `evt_revolutions_1848, evt_communist_manifesto`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `Jupiter-Saturn trine B_`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1848-02-21` period `1846-09-07..1848-02-21`
   - matched: `evt_communist_manifesto, evt_revolutions_1848, evt_opium_wars, evt_womens_suffrage_movement, evt_mughal_empire, evt_atlantic_slave_trade`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`
2. `1846-04-06` period `1846-03-23..1846-05-04`
   - matched: `evt_opium_wars, evt_mughal_empire, evt_atlantic_slave_trade, evt_tokugawa_shogunate, evt_romanticism, evt_french_conquest_algeria`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1859-11-24 - Origin of Species

- Regression: `passed`
- Coverage: `full`
- Warnings: `none`
- Expected events: `evt_origin_of_species`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1859-11-21` period `1859-04-25..1859-11-21`
   - matched: `evt_origin_of_species, evt_opium_wars, evt_taiping_rebellion, evt_indian_rebellion_1857, evt_atlantic_slave_trade, evt_tokugawa_shogunate`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `none`
2. `1858-11-08` period `1858-07-05..1859-01-31`
   - matched: `evt_origin_of_species, evt_opium_wars, evt_taiping_rebellion, evt_indian_rebellion_1857, evt_mughal_empire, evt_atlantic_slave_trade`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `none`
3. `1857-10-26` period `1857-09-07..1857-11-30`
   - matched: `evt_crimean_war, evt_opium_wars, evt_taiping_rebellion, evt_indian_rebellion_1857, evt_mughal_empire, evt_womens_suffrage_movement`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `none`
4. `1856-10-13` period `1856-09-15..1856-10-13`
   - matched: `evt_crimean_war, evt_opium_wars, evt_taiping_rebellion, evt_indian_rebellion_1857, evt_mughal_empire, evt_womens_suffrage_movement`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `none`

### 1861-04-12 - American Civil War

- Regression: `passed`
- Coverage: `full`
- Warnings: `none`
- Expected events: `evt_american_civil_war`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1861-04-08` period `1859-11-07..1861-04-08`
   - matched: `evt_origin_of_species, evt_american_civil_war, evt_opium_wars, evt_taiping_rebellion, evt_indian_rebellion_1857, evt_atlantic_slave_trade`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `none`
2. `1859-08-08` period `1859-07-25..1859-09-12`
   - matched: `evt_origin_of_species, evt_opium_wars, evt_taiping_rebellion, evt_indian_rebellion_1857, evt_atlantic_slave_trade, evt_tokugawa_shogunate`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `none`

### 1868-01-03 - Meiji Restoration

- Regression: `passed`
- Coverage: `full`
- Warnings: `war_bias`
- Expected events: `evt_meiji_restoration`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `Neptune-Uranus square S_`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1867-12-30` period `1866-09-10..1867-12-30`
   - matched: `evt_austro_prussian_war, evt_meiji_restoration, evt_american_civil_war, evt_paraguayan_war, evt_tokugawa_shogunate, evt_atlantic_slave_trade`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `war_bias`
2. `1866-01-22` period `1865-12-11..1866-02-12`
   - matched: `evt_austro_prussian_war, evt_american_civil_war, evt_taiping_rebellion, evt_paraguayan_war, evt_atlantic_slave_trade, evt_tokugawa_shogunate`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `war_bias`

### 1869-11-17 - Periodic table / Suez Canal opening

- Regression: `passed`
- Coverage: `full`
- Warnings: `none`
- Expected events: `evt_periodic_table, evt_suez_canal_opening`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1869-11-15` period `1868-08-10..1869-11-15`
   - matched: `evt_meiji_restoration, evt_periodic_table, evt_suez_canal_opening, evt_franco_prussian_war, evt_paraguayan_war, evt_tokugawa_shogunate`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `none`
2. `1868-03-02` period `1868-03-02..1868-06-15`
   - matched: `evt_meiji_restoration, evt_periodic_table, evt_suez_canal_opening, evt_paraguayan_war, evt_tokugawa_shogunate, evt_atlantic_slave_trade`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `none`

### 1870-07-19 - Franco-Prussian War

- Regression: `passed`
- Coverage: `full`
- Warnings: `none`
- Expected events: `evt_franco_prussian_war`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1870-07-18` period `1869-12-06..1870-07-18`
   - matched: `evt_periodic_table, evt_suez_canal_opening, evt_meiji_restoration, evt_franco_prussian_war, evt_paraguayan_war, evt_second_industrial_revolution`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `none`
2. `1869-06-28` period `1868-12-28..1869-10-11`
   - matched: `evt_meiji_restoration, evt_periodic_table, evt_suez_canal_opening, evt_franco_prussian_war, evt_paraguayan_war, evt_tokugawa_shogunate`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `none`

### 1884-11-15 - Berlin Conference / Sino-French War

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy, war_bias`
- Expected events: `evt_berlin_conference, evt_sino_french_war`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: Fixed: event existed but was displaced by older colonial/global background; boundary-aware long-process sorting now keeps it visible.

#### Top Episodes

1. `1884-11-10` period `1883-07-09..1884-11-10`
   - matched: `evt_sino_french_war, evt_war_of_the_pacific, evt_mahdist_war, evt_berlin_conference, evt_scramble_for_africa, evt_second_industrial_revolution`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `war_bias`
2. `1882-10-09` period `1882-09-11..1882-11-13`
   - matched: `evt_war_of_the_pacific, evt_mahdist_war, evt_scramble_for_africa, evt_second_industrial_revolution, evt_womens_suffrage_movement, evt_sokoto_caliphate`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1895-11-08 - 1895 science and imperial wars

- Regression: `passed`
- Coverage: `full`
- Warnings: `long_process_heavy, war_bias`
- Expected events: `evt_xray_discovery, evt_first_sino_japanese_war, evt_first_italo_ethiopian_war`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `Jupiter-Saturn square B_`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1895-11-04` period `1894-06-25..1895-11-04`
   - matched: `evt_xray_discovery, evt_first_sino_japanese_war, evt_first_italo_ethiopian_war, evt_philippine_revolution, evt_mahdist_war, evt_scramble_for_africa`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `war_bias`
2. `1893-09-18` period `1893-08-28..1893-10-16`
   - matched: `evt_first_sino_japanese_war, evt_mahdist_war, evt_scramble_for_africa, evt_second_industrial_revolution, evt_womens_suffrage_movement, evt_progressive_era`
   - context: `none`
   - event mix warnings: `long_process_heavy`
   - episode warnings: `none`

### 1898-04-21 - Spanish-American War

- Regression: `passed`
- Coverage: `full`
- Warnings: `war_bias`
- Expected events: `evt_spanish_american_war`
- Missing expected events: `none`
- Top episode missing expected events: `none`
- Expected context events: `none`
- Missing expected context events: `none`
- Expected cycles: `none`
- Missing expected cycles: `none`
- Manual audit: sensible_top_n
- Root-cause review: none

#### Top Episodes

1. `1898-04-18` period `1896-10-26..1898-04-18`
   - matched: `evt_spanish_american_war, evt_xray_discovery, evt_philippine_revolution, evt_first_italo_ethiopian_war, evt_first_sino_japanese_war, evt_boxer_rebellion`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `war_bias`
2. `1896-06-15` period `1896-04-27..1896-07-06`
   - matched: `evt_xray_discovery, evt_first_italo_ethiopian_war, evt_philippine_revolution, evt_first_sino_japanese_war, evt_mahdist_war, evt_scramble_for_africa`
   - context: `none`
   - event mix warnings: `none`
   - episode warnings: `war_bias`
