from datetime import date

from app.services.experience import compute_experience

TODAY = date(2025, 6, 15)


def exp(start, end=None, current=False, company="ACME"):
    return {"company": company, "start_date": start, "end_date": end, "is_current": current}


def test_single_job():
    total, warnings = compute_experience([exp("2020-01", "2020-06")], TODAY)
    assert total == 6
    assert warnings == []


def test_two_overlapping_jobs():
    total, _ = compute_experience([exp("2020-01", "2020-12"), exp("2020-06", "2021-03")], TODAY)
    assert total == 15  # Jan 2020 – Mar 2021


def test_two_sequential_jobs():
    total, _ = compute_experience([exp("2019-01", "2019-06"), exp("2020-01", "2020-06")], TODAY)
    assert total == 12


def test_current_job():
    total, _ = compute_experience([exp("2024-07", None, current=True)], TODAY)
    assert total == 12  # Jul 2024 – Jun 2025


def test_year_only_dates():
    total, _ = compute_experience([exp("2019", "2020")], TODAY)
    assert total == 24


def test_year_only_end_in_current_year_is_capped():
    total, _ = compute_experience([exp("2025", "2025")], TODAY)
    assert total == 6


def test_missing_end_date_warns():
    total, warnings = compute_experience([exp("2020-01", None, company="Foo")], TODAY)
    assert total == 0
    assert warnings and "Foo" in warnings[0] and "missing end date" in warnings[0]


def test_end_before_start_warns():
    total, warnings = compute_experience([exp("2021-05", "2020-01")], TODAY)
    assert total == 0
    assert len(warnings) == 1


def test_missing_start_warns():
    total, warnings = compute_experience([exp(None, "2020-01")], TODAY)
    assert total == 0
    assert len(warnings) == 1


def test_empty_list():
    assert compute_experience([], TODAY) == (0, [])


def test_jan_to_dec_same_year_is_12():
    total, _ = compute_experience([exp("2022-01", "2022-12")], TODAY)
    assert total == 12


def test_adjacent_jobs_not_merged_double():
    total, _ = compute_experience([exp("2020-01", "2020-06"), exp("2020-07", "2020-12")], TODAY)
    assert total == 12
