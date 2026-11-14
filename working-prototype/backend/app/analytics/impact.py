"""Impact on editable inputs, by the attributable-share method.

The share of injuries attributable to an exposure is (RR - 1) / RR. With the published
relative risks (1.17 on heat days, 1.36 on a fourth or later night), the injuries a year
the system could prevent are: injuries x (hot share x AF heat + night share x AF night)
x share of warnings acted on x effectiveness of the action.
"""

from dataclasses import asdict, dataclass

RR_HEAT = 1.17
RR_NIGHT = 1.36


@dataclass(frozen=True)
class ImpactInputs:
    lti_per_year: float = 40
    hot_share: float = 0.40
    night_share: float = 0.20
    acted_on: float = 0.70
    effectiveness: float = 0.50
    workdays_per_injury: float = 20


def impact(inputs: ImpactInputs) -> dict:
    af_heat = (RR_HEAT - 1) / RR_HEAT
    af_night = (RR_NIGHT - 1) / RR_NIGHT
    attributable = inputs.lti_per_year * (
        inputs.hot_share * af_heat + inputs.night_share * af_night
    )
    avoided = attributable * inputs.acted_on * inputs.effectiveness
    return {
        "inputs": asdict(inputs),
        "attributable_lti": round(attributable, 2),
        "lti_avoided": round(avoided, 1),
        "workdays_avoided": round(avoided * inputs.workdays_per_injury),
        "not_counted": [
            "Heat illness that never becomes an injury",
            "Slow harm such as kidney strain over a summer",
            "Sickness absence",
            "Disruption to a vessel call",
        ],
    }
