"""Timeline date engine, checked against PRD v1.3 sections 6 (rules) and 8.4 (edge cases)."""

from datetime import date, timedelta

import pytest

from app.opt.timeline import (
    DateState,
    DueType,
    Risk,
    StartPreference,
    TimelineInput,
    TimelineParams,
    WindowStatus,
    compute_timeline,
)

P = date(2027, 6, 11)  # PRD 6.4 example values
S = date(2027, 7, 12)
R = date(2027, 3, 20)
PARAMS = TimelineParams(
    t_school=14,  # business days
    t_uscis_standard=90,  # calendar days
    t_uscis_premium=30,  # business days
    buffer=14,
    school_window_open=date(2027, 2, 1),
)


def offer(**kw) -> TimelineInput:
    base = dict(program_end=P, today=date(2027, 1, 4), has_offer=True, offer_start=S)
    return TimelineInput(**{**base, **kw})


def no_offer(**kw) -> TimelineInput:
    base = dict(program_end=P, today=date(2027, 1, 4), has_offer=False)
    return TimelineInput(**{**base, **kw})


# --- Branch 1: has an offer start date (backward from S) ---


def test_offer_matches_prd_example():
    res = compute_timeline(offer(dso_rec=R), PARAMS)
    assert res.node("N2").date == date(2027, 3, 20)
    assert res.node("N3").date == date(2027, 3, 30)
    assert res.node("N1").date == date(2027, 3, 10)  # N3 - 14 business days (PRD 6.4 used calendar days: 03-16)
    assert res.node("N1b").date == R  # once R is entered it wins
    assert res.node("N4").date == date(2027, 4, 19)
    assert res.node("N5").date == S
    assert res.risks == []


def test_offer_due_types():
    res = compute_timeline(offer(dso_rec=R), PARAMS)
    assert res.node("N2").due_type == DueType.FEDERAL
    assert res.node("N3").due_type == DueType.RECOMMENDED
    assert res.node("N4").due_type == DueType.FEDERAL
    assert res.node("N6").due_type == DueType.ESTIMATE
    assert res.node("N7").due_type == DueType.EVENT_BASED


def test_offer_at_risk_when_start_is_too_close_to_filing_window():
    res = compute_timeline(offer(offer_start=date(2027, 6, 20)), PARAMS)
    assert Risk.AT_RISK in res.risks
    assert res.node("N3").date == date(2027, 3, 15)  # not before the I-20 is expected (N1b)


def test_offer_at_risk_when_recommended_date_already_passed():
    res = compute_timeline(offer(today=date(2027, 4, 1)), PARAMS)
    assert Risk.AT_RISK in res.risks


def test_offer_gap_warning_when_start_after_p_plus_60():
    res = compute_timeline(offer(offer_start=date(2027, 9, 1)), PARAMS)
    assert Risk.GAP_WARNING in res.risks
    assert res.node("N5").date == date(2027, 8, 10)


def test_offer_without_r_marks_federal_dates_unconfirmed():
    res = compute_timeline(offer(), PARAMS)
    assert res.node("N2").date == date(2027, 3, 13)
    assert res.node("N4").date == date(2027, 8, 10)
    assert res.node("N4").date_state == DateState.PARTIAL


def test_offer_start_on_or_before_program_end_is_out_of_scope():
    res = compute_timeline(offer(offer_start=P), PARAMS)
    assert res.risks == [Risk.OUT_OF_SCOPE]
    assert res.nodes == []


def test_n1_not_earlier_than_school_window():
    params = PARAMS.model_copy(update={"school_window_open": date(2027, 3, 20)})
    res = compute_timeline(offer(dso_rec=R), params)
    assert res.node("N1").date == date(2027, 3, 20)


def test_n1_unconfirmed_without_school_window():
    params = PARAMS.model_copy(update={"school_window_open": None})
    res = compute_timeline(offer(dso_rec=R), params)
    assert res.node("N1").date == date(2027, 3, 10)
    assert res.node("N1").date_state == DateState.PARTIAL


def test_n1b_uses_actual_request_date_until_r_is_known():
    res = compute_timeline(offer(i20_request=date(2027, 3, 1)), PARAMS)
    assert res.node("N1b").date == date(2027, 3, 19)  # + 14 business days
    assert res.node("N1b").due_type == DueType.ESTIMATE


def test_premium_processing_shortens_uscis_time():
    res = compute_timeline(offer(dso_rec=R, premium=True), PARAMS)
    # (S - 14) - 30 business days, skipping Juneteenth (observed 6/18) and Memorial Day
    assert res.node("N3").date == date(2027, 5, 13)


def test_n6_and_n7_follow_actual_filing_date():
    res = compute_timeline(offer(dso_rec=R, uscis_receipt=date(2027, 3, 25)), PARAMS)
    assert res.node("N6").date == date(2027, 6, 23)
    assert res.node("N7").date == S


# --- Branch 2: no offer (forward from the filing window) ---


def test_no_offer_before_window_opens():
    res = compute_timeline(no_offer(), PARAMS)
    assert res.node("N1").date == date(2027, 2, 23)  # (P - 90) - 14 business days
    assert res.node("N2").date == date(2027, 3, 13)
    assert res.node("N3").date == date(2027, 3, 15)  # I-20 expected 2/23 + 14 business days
    assert res.node("N4").date == date(2027, 8, 10)
    assert res.node("N5").date is None
    assert res.node("N5").date_state == DateState.UNKNOWN


def test_no_offer_recommends_filing_today_once_window_is_open():
    res = compute_timeline(no_offer(today=date(2027, 4, 1)), PARAMS)
    assert res.node("N3").date == date(2027, 4, 1)


def test_no_offer_asap_start_is_day_after_program_end():
    res = compute_timeline(no_offer(start_preference=StartPreference.ASAP), PARAMS)
    assert res.node("N5").date == date(2027, 6, 12)


def test_no_offer_specific_start_date():
    pick = date(2027, 7, 1)
    res = compute_timeline(
        no_offer(start_preference=StartPreference.SPECIFIC_DATE, preferred_start=pick), PARAMS
    )
    assert res.node("N5").date == pick


def test_no_offer_start_outside_p_plus_1_to_p_plus_60_rejected():
    with pytest.raises(ValueError):
        compute_timeline(
            no_offer(start_preference=StartPreference.SPECIFIC_DATE, preferred_start=date(2027, 8, 20)),
            PARAMS,
        )


def test_no_offer_with_r():
    res = compute_timeline(no_offer(dso_rec=R), PARAMS)
    assert res.node("N2").date == R
    assert res.node("N4").date == date(2027, 4, 19)
    assert res.node("N4").date_state == DateState.USER_CONFIRMED


# --- Edge cases (PRD 8.4) ---


def test_window_closed_after_p_plus_60_when_not_filed():
    res = compute_timeline(no_offer(today=date(2027, 8, 11)), PARAMS)
    assert res.window == WindowStatus.CLOSED
    assert res.risks == [Risk.WINDOW_CLOSED]
    assert res.nodes == []


def test_window_not_closed_if_already_filed():
    res = compute_timeline(
        no_offer(today=date(2027, 8, 11), dso_rec=R, uscis_receipt=date(2027, 4, 1)), PARAMS
    )
    assert Risk.WINDOW_CLOSED not in res.risks
    assert res.nodes


def test_conflict_when_r_plus_30_before_p_minus_90():
    res = compute_timeline(offer(dso_rec=date(2027, 2, 1)), PARAMS)
    assert Risk.CONFLICT in res.risks
    for node_id in ("N2", "N3", "N4"):
        assert res.node(node_id).date is None
        assert res.node(node_id).date_state == DateState.CONFLICT


def test_conflict_when_r_after_uscis_receipt():
    res = compute_timeline(offer(dso_rec=date(2027, 3, 25), uscis_receipt=date(2027, 3, 20)), PARAMS)
    assert Risk.CONFLICT in res.risks


def test_more_than_12_months_out_shows_only_window_opening():
    res = compute_timeline(no_offer(today=date(2026, 5, 1)), PARAMS)
    assert res.too_early is True
    assert [n.id for n in res.nodes] == ["N2"]


@pytest.mark.parametrize(
    "today,expected",
    [
        (date(2027, 3, 12), WindowStatus.NOT_OPEN),
        (date(2027, 3, 13), WindowStatus.OPEN),
        (date(2027, 6, 11), WindowStatus.OPEN),
        (date(2027, 6, 12), WindowStatus.AFTER_PROGRAM_END),
        (date(2027, 8, 10), WindowStatus.AFTER_PROGRAM_END),
        (date(2027, 8, 11), WindowStatus.CLOSED),
    ],
)
def test_window_status(today, expected):
    assert compute_timeline(no_offer(today=today), PARAMS).window == expected


def test_nodes_sorted_by_date_with_unknown_dates_last():
    res = compute_timeline(no_offer(), PARAMS)
    dated = [n.date for n in res.nodes if n.date is not None]
    assert dated == sorted(dated)
    assert res.nodes[-1].date is None


def test_offer_at_risk_when_i20_request_target_passed_and_not_requested():
    res = compute_timeline(offer(today=date(2027, 3, 20)), PARAMS)
    assert res.node("N1").date < date(2027, 3, 20)
    assert Risk.AT_RISK in res.risks


def test_offer_not_at_risk_once_i20_requested():
    res = compute_timeline(offer(today=date(2027, 3, 20), i20_request=date(2027, 3, 10)), PARAMS)
    assert Risk.AT_RISK not in res.risks


def test_after_filing_n5_is_the_start_date_on_the_i765():
    filed_start = date(2027, 7, 1)
    res = compute_timeline(
        offer(dso_rec=R, uscis_receipt=date(2027, 3, 25), requested_start=filed_start), PARAMS
    )
    assert res.node("N5").date == filed_start
    assert res.node("N7").date == max(filed_start, date(2027, 6, 23))


# --- Reviewed UW policy (2026-11-16): business days, school I-20 deadline, SEVIS vs I-20 issue date ---

UW_DEADLINE = date(2027, 7, 21)  # P + 40 calendar days
UW = PARAMS.model_copy(update={"school_request_deadline": UW_DEADLINE})


def test_school_request_deadline_node():
    res = compute_timeline(offer(dso_rec=R), UW)
    n1d = res.node("N1d")
    assert n1d.date == UW_DEADLINE
    assert n1d.due_type == DueType.SCHOOL


def test_no_school_deadline_node_without_policy_value():
    res = compute_timeline(offer(dso_rec=R), PARAMS)
    assert "N1d" not in [n.id for n in res.nodes]


def test_n1_never_after_school_request_deadline():
    res = compute_timeline(offer(offer_start=date(2027, 12, 1)), UW)
    assert res.node("N1").date == UW_DEADLINE


def test_at_risk_when_school_deadline_passed_and_i20_not_requested():
    res = compute_timeline(no_offer(today=date(2027, 7, 22)), UW)
    assert Risk.AT_RISK in res.risks


def test_not_at_risk_after_school_deadline_once_i20_requested():
    res = compute_timeline(no_offer(today=date(2027, 7, 22), i20_request=date(2027, 7, 1)), UW)
    assert Risk.AT_RISK not in res.risks


def test_issue_date_stands_in_for_sevis_date_with_warning():
    issued = date(2027, 3, 20)
    res = compute_timeline(offer(i20_issue=issued), PARAMS)
    assert res.node("N2").date == issued
    assert res.node("N4").date == date(2027, 4, 19)  # issue date + 30
    assert res.node("N4").date_state == DateState.PARTIAL
    assert Risk.SEVIS_DATE_UNCONFIRMED in res.risks


def test_sevis_date_wins_over_issue_date():
    res = compute_timeline(offer(dso_rec=date(2027, 3, 18), i20_issue=date(2027, 3, 20)), PARAMS)
    assert res.node("N4").date == date(2027, 4, 17)
    assert res.node("N4").date_state == DateState.USER_CONFIRMED
    assert Risk.SEVIS_DATE_UNCONFIRMED not in res.risks


def test_i20_arrival_is_the_issue_date_when_known():
    res = compute_timeline(offer(dso_rec=date(2027, 3, 18), i20_issue=date(2027, 3, 20)), PARAMS)
    assert res.node("N1b").date == date(2027, 3, 20)


def test_premium_ead_estimate_uses_business_days():
    res = compute_timeline(offer(dso_rec=R, premium=True, uscis_receipt=date(2027, 3, 1)), PARAMS)
    assert res.node("N6").date == date(2027, 4, 12)  # 3/1 + 30 business days


# --- You can't file the I-765 before the OPT I-20 arrives ---


def test_no_offer_recommended_filing_not_before_i20_arrives():
    res = compute_timeline(no_offer(), UW)
    assert res.node("N3").date >= res.node("N1b").date


def test_offer_recommended_filing_not_before_i20_arrives():
    # UW opens I-20 requests at P - 90, so the I-20 (3/13 + 14 business days = 4/1) lands after S - T_u - B = 3/30.
    res = compute_timeline(offer(), UW.model_copy(update={"school_window_open": date(2027, 3, 13)}))
    assert res.node("N3").date == date(2027, 4, 1)
    assert res.node("N3").date >= res.node("N1b").date
    assert Risk.AT_RISK in res.risks  # filing later than the offer needs


def test_ead_estimate_follows_the_later_filing_date():
    res = compute_timeline(no_offer(), UW)
    assert res.node("N6").date == res.node("N3").date + timedelta(days=90)


def test_known_recommendation_date_unchanged():
    res = compute_timeline(offer(dso_rec=R), PARAMS)
    assert res.node("N3").date == date(2027, 3, 30)
