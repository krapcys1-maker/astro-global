from __future__ import annotations

from scripts.compare_known_resonance_event_drift import (
    _counter_delta,
    build_drift_report,
    render_markdown,
)


def _case(
    query_date: str,
    *,
    matched_event_ids: tuple[str, ...],
    expected_event_ids: tuple[str, ...] = (),
    candidate_long_process_count: int = 0,
    selected_long_process_count: int = 0,
    event_mix_warnings: tuple[str, ...] = (),
) -> dict:
    selected_count = len(matched_event_ids)
    candidate_count = selected_count + candidate_long_process_count
    selected_instant_count = selected_count - selected_long_process_count
    candidate_instant_count = candidate_count - candidate_long_process_count
    return {
        "query_date": query_date,
        "expectation_evaluation": {
            "expected_event_ids": list(expected_event_ids),
        },
        "top_episodes": [
            {
                "matched_events": [
                    {
                        "event_id": event_id,
                        "display_date": "2020",
                    }
                    for event_id in matched_event_ids
                ],
                "event_mix_diagnostic": {
                    "candidate_pool_event_kind_counts": {
                        "instant_event": candidate_instant_count,
                        "long_process": candidate_long_process_count,
                    },
                    "selected_event_kind_counts": {
                        "instant_event": selected_instant_count,
                        "long_process": selected_long_process_count,
                    },
                    "warnings": list(event_mix_warnings),
                },
            }
        ],
    }


def test_counter_delta_reports_only_changed_counts() -> None:
    assert _counter_delta({"war_bias": 4, "thin_history": 1}, {"war_bias": 3}) == {
        "thin_history": -1,
        "war_bias": -1,
    }


def test_drift_report_detects_removed_expected_event_regression() -> None:
    baseline = {
        "warning_counts": {"war_bias": 1},
        "event_mix_warning_counts": {},
        "cases": [
            _case(
                "2020-01-12",
                matched_event_ids=("evt_expected", "evt_old"),
                expected_event_ids=("evt_expected",),
            )
        ],
    }
    current = {
        "warning_counts": {},
        "event_mix_warning_counts": {"long_process_heavy": 1},
        "cases": [
            _case(
                "2020-01-12",
                matched_event_ids=("evt_new",),
                expected_event_ids=("evt_expected",),
                candidate_long_process_count=8,
                selected_long_process_count=1,
                event_mix_warnings=("long_process_heavy",),
            )
        ],
    }

    report = build_drift_report(
        baseline=baseline,
        current=current,
        baseline_label="before",
        current_label="after",
    )

    case_delta = report["case_deltas"][0]
    assert report["cases_compared"] == 1
    assert report["matched_event_change_count"] == 1
    assert report["expected_event_regression_count"] == 1
    assert case_delta["added_matched_event_ids"] == ("evt_new",)
    assert case_delta["removed_matched_event_ids"] == ("evt_expected", "evt_old")
    assert case_delta["lost_expected_event_ids"] == ("evt_expected",)
    assert case_delta["drift_warnings"] == (
        "matched_event_set_changed",
        "matched_events_removed",
        "expected_event_regression",
        "selected_long_process_share_increased",
        "candidate_long_process_share_increased",
        "new_event_mix_warning",
    )


def test_render_markdown_summarizes_drift_report() -> None:
    report = build_drift_report(
        baseline={
            "warning_counts": {},
            "event_mix_warning_counts": {},
            "cases": [_case("2020-01-12", matched_event_ids=("evt_a",))],
        },
        current={
            "warning_counts": {},
            "event_mix_warning_counts": {},
            "cases": [_case("2020-01-12", matched_event_ids=("evt_a", "evt_b"))],
        },
        baseline_label="before",
        current_label="after",
    )

    rendered = render_markdown(report)

    assert "# Known Resonance Event Drift" in rendered
    assert "- Added matched events: `evt_b`" in rendered
    assert "- Expected-event regressions: 0" in rendered
