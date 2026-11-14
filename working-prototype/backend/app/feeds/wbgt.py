"""Wet bulb globe temperature (WBGT) from ordinary weather readings.

WBGT is the heat-stress measure work-rest rules use. We estimate it from air
temperature, relative humidity and sunshine:

- natural wet bulb from Stull's 2011 formula for wet-bulb temperature;
- shade WBGT = 0.7 x wet bulb + 0.3 x air temperature;
- outdoor work adds a radiant load proportional to sunshine (0.0035 C per W/m2).

The simpler Australian Bureau of Meteorology approximation was rejected: on humid
Gulf nights it reads several degrees above measured WBGT.
"""

from math import atan, sqrt

RADIANT_C_PER_WM2 = 0.0035
TIER_FLOORS = (27.0, 30.0, 32.0)  # tier 1, tier 2, tier 3


def stull_wet_bulb(temp_c: float, rh_pct: float) -> float:
    t, rh = temp_c, rh_pct
    return (
        t * atan(0.151977 * sqrt(rh + 8.313659))
        + atan(t + rh)
        - atan(rh - 1.676331)
        + 0.00391838 * rh**1.5 * atan(0.023101 * rh)
        - 4.686035
    )


def estimate_wbgt(temp_c: float, rh_pct: float, radiation_wm2: float = 0.0) -> float:
    shade = 0.7 * stull_wet_bulb(temp_c, rh_pct) + 0.3 * temp_c
    return round(shade + RADIANT_C_PER_WM2 * max(radiation_wm2, 0.0), 2)


def heat_tier(wbgt_c: float) -> int:
    """0 below 27 C, 1 from 27, 2 from 30, 3 from 32."""
    return sum(1 for floor in TIER_FLOORS if wbgt_c >= floor)
