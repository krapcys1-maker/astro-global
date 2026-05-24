# Historical Balance Audit - Astro Global

Date: 2026-05-24

## Scope

- Dataset: `services/historical/seeds/curated_events.csv` (225 events).
- Visibility sample: 155 unique curated-event start/display dates queried through real `POST /resonance/search` with `swiss_1500_now_global_slow_v1.npz`.
- Top episode only was used for dominance metrics because this is what the Explorer highlights first.
- Goal: do not hide wars; make the civilizational mix legible.

## Dataset Distribution

| Period | Events | War | Conflict/crisis aggregate | Science/institution/culture/economy aggregate | Top categories |
| --- | ---: | ---: | ---: | ---: | --- |
| all | 225 | 30.7% | 55.6% | 27.1% | war 69, revolution 25, science_technology 23, institution 21, geopolitical_transition 8 |
| pre1900 | 86 | 38.4% | 53.5% | 22.1% | war 33, revolution 12, political_transition 5, science_technology 5, colonial_expansion 4 |
| modern | 139 | 25.9% | 56.8% | 30.2% | war 36, institution 19, science_technology 18, revolution 13, epidemic 6 |

## Explorer Visibility Metrics

| Period | Requests | Selected war share | War-dominant top episodes | Top event is war | Episodes with war >=50% | Episodes with conflict/crisis >=50% | Science/institution/culture present | Long-process >=50% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 155 | 31.5% | 56.8% | 23.9% | 29.0% | 65.8% | 61.9% | 38.7% |
| pre1900 | 72 | 24.0% | 48.6% | 44.4% | 19.4% | 36.1% | 56.9% | 75.0% |
| modern | 83 | 37.9% | 63.9% | 6.0% | 37.3% | 91.6% | 66.3% | 7.2% |

## Root Cause Analysis

- Dataset bias exists, but it is not simply `all war`: war is 30.7% of all curated events. The broader conflict/crisis aggregate is 55.6%, so the seed naturally leans toward disruptive public-history anchors.
- Pre-1900 is mostly a long-process visibility issue: 75.0% of sampled top episodes have long_process >=50%, while selected war share is 24.0%. Empires, trade systems, reformation, slavery and industrialization stay visible for many windows.
- Modern results are genuinely disruption-heavy in the selected windows: selected war share is 37.9%, and 91.6% of sampled top episodes have conflict/crisis >=50%. This is partly dataset density and partly recent-history reality around wars, epidemics, economic crises and political shocks.
- The planetary score is not using historical categories. No evidence points to planetary scoring as the direct root cause; the visibility layer comes from historical event selection after resonance search.
- `event_query.EVENT_KIND_RANKS` prioritizes crisis/instant events before revolution/war, then transition/institution/long_process. That protects exact events, but it does not category-balance the final six matched events.
- Confidence is not the main cause: high-confidence non-war events exist, but if a window has many conflict records they still fill the list.
- The old Explorer presentation amplified the issue: linear matched_events lists made conflict titles visually dominate, and the user had no category lens to see science, institutions, economy or broad context separately.

## Manual Date Read

| Date | Top best date | Visible mix | UX impression |
| --- | --- | --- | --- |
| 1543-01-01 | 1542-12-28 | war, war, religious_reformation, science_technology, political_transition, economic_transition | Scientific Revolution is present, but first two titles are wars; feels more violent than the actual category mix. |
| 1648-10-24 | 1648-10-19 | diplomatic_settlement, war, war, religious_reformation, war, geopolitical_transition | War-heavy by historical nature; Peace of Westphalia appears first and should be read as diplomatic settlement plus war context. |
| 1789-07-14 | 1789-07-13 | revolution, geopolitical_transition, economic_transition, economic_institution, political_transition, political_transition | Not war-heavy; revolution/transition/economy with Enlightenment context. Long-process background is the main issue. |
| 1848-02-24 | 1848-02-21 | political_ideology, revolution, war, civil_rights, political_transition, economic_transition | Good mixed result: ideology, revolution, war, civil rights and long background. |
| 1869-11-17 | 1869-11-15 | science_technology, infrastructure, political_transition, war, war, economic_transition | Good civilizational mix: periodic table, Suez, Meiji, then wars and industrialization. |
| 1989-11-09 | 1989-11-06 | political_crisis, geopolitical_transition, institution, war, war, war | Top three are crisis/transition/institution, but half the list is wars; needs category framing. |
| 2020-01-12 | 2020-01-06 | epidemic, civil_rights, science_technology, war, war, disaster | Mixed crisis/science/war/disaster; war is not majority but the date feels crisis-heavy. |
| 2022-02-24 | 2022-02-21 | civil_rights, epidemic, science_technology, war, science_technology, institution | Surprisingly mixed in backend output: civil rights/epidemic/science/war/science/institution; UI should prevent one war title from defining the whole result. |

## UX Change Made

- Explorer now renders category badges on event cards and timeline episode cards.
- Explorer now groups matched/context events by civilizational category group.
- Explorer now shows a `Civilizational event mix` bar summary for the selected episode.
- Explorer now has event-lens toggles: All evidence, Hard disruption, Science & technology, Institutions, Society & culture, Economy & infrastructure, Civilizational background.
- The default remains `All evidence`; wars are not hidden or down-ranked. Filters are presentation-only and do not change backend truth.

## Manual Frontend Verification

- URL tested: `http://127.0.0.1:5173/#explorer` against `http://127.0.0.1:8765`.
- Browser run: 9 Explorer searches through the real form flow; 0 network failures, 0 console errors, 0 runtime exceptions.
- Dates checked: 1789-07-14, 1848-02-24, 2020-01-12, 2026-05-24, 1543-01-01, 1648-10-24, 1869-11-17, 1989-11-09, 2022-02-24.
- UI/backend comparison: top matched/context event titles from the backend response were visible in Explorer for every checked date.
- Category filter check: `Hard disruption` filter activated and reduced the event list to the matching category without issuing a backend request or changing backend state.
- Screenshots saved locally: `work/screenshots/balance_explorer_17890714_after.png`, `work/screenshots/balance_explorer_20200112_after.png`.

## Safe Missing Events To Consider Later

These are suggestions only; no data was added in this patch.

1. Telegraph public line, 1844 - communications technology.
2. Telephone patent/first practical call, 1876 - communications technology.
3. British Slave Trade Act, 1807 - social/economic reform counterweight to Atlantic slave trade.
4. Louisiana Purchase, 1803 - geopolitical/economic state expansion marker.
5. Haiti independence, 1804 - decolonization/revolutionary state marker.
6. July Revolution / Revolutions of 1830 - political transition marker around the Algeria case window.
7. Emancipation of Russian serfs, 1861 - major social reform.
8. German Empire proclamation, 1871 - state/institution marker after Franco-Prussian War.
9. International Meridian Conference, 1884 - time-standard/institutional science marker.
10. Koch tuberculosis discovery, 1882 or Lister antiseptic surgery, 1865 - medicine/germ-theory marker.

## Conclusion

The audit does not support saying the system is balanced. It supports a narrower claim: the dataset is not pure war, but Explorer visibility is disruption-heavy, especially in modern windows, and pre-1900 still carries a long-process-heavy character. The safest near-term fix is UX category framing, not ranking tuning or artificial event suppression.
