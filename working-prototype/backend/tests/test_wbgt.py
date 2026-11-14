import pytest

from app.feeds.wbgt import estimate_wbgt, heat_tier, stull_wet_bulb


def test_stull_wet_bulb_reference_value() -> None:
    # Stull (2011) gives about 13.7 C at 20 C and 50 percent humidity.
    assert stull_wet_bulb(20, 50) == pytest.approx(13.7, abs=0.1)


def test_wbgt_known_values() -> None:
    # Shade, 40 C and 40 percent humidity.
    assert estimate_wbgt(40, 40) == pytest.approx(32.0, abs=0.3)
    # Abu Dhabi, 29 July 2025 at 12:00 local: 45.1 C, 17 percent, 858 W/m2 of sun.
    assert estimate_wbgt(45.1, 17, 858) == pytest.approx(34.0, abs=0.3)
    # Same night: 33.5 C and 72 percent, no sun.
    assert estimate_wbgt(33.5, 72) == pytest.approx(30.5, abs=0.3)


def test_heat_tier_boundaries() -> None:
    assert [heat_tier(v) for v in (26.9, 27.0, 29.9, 30.0, 31.9, 32.0, 35.0)] == [
        0,
        1,
        1,
        2,
        2,
        3,
        3,
    ]
