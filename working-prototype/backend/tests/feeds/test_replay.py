from datetime import datetime

from seed.deck_replay import deck_series


def test_story_evening_crosses_the_limit_for_half_an_hour() -> None:
    series = deck_series("Berth 2", datetime(2026, 7, 29, 15, 0), datetime(2026, 7, 29, 16, 30), 10)
    first_half_hour = [v for t, v in series if t <= datetime(2026, 7, 29, 15, 30)]
    assert len(first_half_hour) == 4 and all(v > 32 for v in first_half_hour)
    assert series[-1][1] < 32.5
