"""Deterministic balance model for Reincarne Logic's Serpentine Sense.

The model answers one narrow question: given a predicted threat lead time and a
player response budget, how much world-time dilation is justified? It is kept
free of game-engine dependencies so designers can sweep values in CI.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable


class SenseChannel(str, Enum):
    COIL_INSTINCT = "coil_instinct"
    AURA_SIGHT = "aura_sight"
    AETHERWARE_ORACLE = "aetherware_oracle"
    HEX_ECHO = "hex_echo"


class ThreatFamily(str, Enum):
    KINETIC_FRACTURE = "kinetic_fracture"
    AURA_PREDATION = "aura_predation"
    HEX_WEAVE = "hex_weave"
    AETHER_SURGE = "aether_surge"
    CYBER_INTRUSION = "cyber_intrusion"


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    if edge0 >= edge1:
        raise ValueError("smoothstep requires edge0 < edge1")
    normalized = clamp((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return normalized * normalized * (3.0 - 2.0 * normalized)


@dataclass(frozen=True)
class SenseTuning:
    """Player-facing and resource-facing tuning values.

    All latency and budget values are in real seconds. ``min_time_scale`` is
    world seconds advanced per real second, so 0.10 means 10% world speed.
    """

    target_decision_seconds: float = 0.90
    cue_latency_seconds: float = 0.17
    input_latency_seconds: float = 0.08
    min_time_scale: float = 0.10
    min_assist_confidence: float = 0.45
    full_assist_confidence: float = 0.85
    ambiguity_budget_multiplier: float = 0.35
    ambiguity_assist_penalty: float = 0.35
    reserve_cost_rate: float = 7.5
    max_reserve: float = 100.0

    def __post_init__(self) -> None:
        positive = {
            "target_decision_seconds": self.target_decision_seconds,
            "cue_latency_seconds": self.cue_latency_seconds,
            "input_latency_seconds": self.input_latency_seconds,
            "reserve_cost_rate": self.reserve_cost_rate,
            "max_reserve": self.max_reserve,
        }
        if any(value < 0 for value in positive.values()):
            raise ValueError("time and reserve tuning values cannot be negative")
        if not 0 < self.min_time_scale <= 1:
            raise ValueError("min_time_scale must be in (0, 1]")
        if not 0 <= self.min_assist_confidence < self.full_assist_confidence <= 1:
            raise ValueError("confidence thresholds must satisfy 0 <= min < full <= 1")
        if not 0 <= self.ambiguity_assist_penalty <= 1:
            raise ValueError("ambiguity_assist_penalty must be in [0, 1]")


@dataclass(frozen=True)
class ThreatSignature:
    lead_seconds: float
    severity: float
    confidence: float
    ambiguity: float = 0.0
    family: ThreatFamily = ThreatFamily.KINETIC_FRACTURE
    channel: SenseChannel = SenseChannel.COIL_INSTINCT

    def __post_init__(self) -> None:
        if self.lead_seconds < 0:
            raise ValueError("lead_seconds cannot be negative")
        for name in ("severity", "confidence", "ambiguity"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0, 1]")


@dataclass(frozen=True)
class SenseDecision:
    requested_time_scale: float
    time_scale: float
    real_window_seconds: float
    usable_response_seconds: float
    requested_decision_seconds: float
    assist_weight: float
    reserve_cost: float
    reserve_limited: bool
    whisper_only: bool
    target_met: bool
    unavoidable_at_minimum_scale: bool


def requested_decision_budget(
    threat: ThreatSignature, tuning: SenseTuning
) -> float:
    """Increase deliberation time slightly when the signal is ambiguous."""

    return tuning.target_decision_seconds * (
        1.0 + threat.ambiguity * tuning.ambiguity_budget_multiplier
    )


def reserve_cost(
    *, lead_seconds: float, time_scale: float, severity: float, tuning: SenseTuning
) -> float:
    """Cost of maintaining Crown Flare for this threat.

    Cost approaches zero at normal time and rises with both slowdown duration
    and threat severity.
    """

    if time_scale <= 0:
        raise ValueError("time_scale must be positive")
    real_window = lead_seconds / time_scale
    return (
        tuning.reserve_cost_rate
        * (1.0 - time_scale)
        * real_window
        * (0.5 + 0.5 * severity)
    )


def _reserve_limited_scale(
    *,
    desired_scale: float,
    reserve: float,
    threat: ThreatSignature,
    tuning: SenseTuning,
) -> tuple[float, float, bool]:
    desired_cost = reserve_cost(
        lead_seconds=threat.lead_seconds,
        time_scale=desired_scale,
        severity=threat.severity,
        tuning=tuning,
    )
    if desired_cost <= reserve + 1e-9:
        return desired_scale, desired_cost, False
    if reserve <= 0:
        return 1.0, 0.0, True

    # Cost decreases monotonically as scale approaches 1. Binary search finds
    # the strongest slowdown the current reserve can actually fund.
    lower = desired_scale
    upper = 1.0
    for _ in range(64):
        candidate = (lower + upper) / 2.0
        candidate_cost = reserve_cost(
            lead_seconds=threat.lead_seconds,
            time_scale=candidate,
            severity=threat.severity,
            tuning=tuning,
        )
        if candidate_cost > reserve:
            lower = candidate
        else:
            upper = candidate

    final_scale = upper
    final_cost = min(
        reserve,
        reserve_cost(
            lead_seconds=threat.lead_seconds,
            time_scale=final_scale,
            severity=threat.severity,
            tuning=tuning,
        ),
    )
    return final_scale, final_cost, True


def evaluate_threat(
    threat: ThreatSignature,
    *,
    reserve: float = 100.0,
    tuning: SenseTuning | None = None,
) -> SenseDecision:
    tuning = tuning or SenseTuning()
    if reserve < 0:
        raise ValueError("reserve cannot be negative")
    reserve = min(reserve, tuning.max_reserve)

    decision_budget = requested_decision_budget(threat, tuning)
    total_budget = (
        decision_budget
        + tuning.cue_latency_seconds
        + tuning.input_latency_seconds
    )
    requested_scale = clamp(
        threat.lead_seconds / total_budget if total_budget > 0 else 1.0,
        tuning.min_time_scale,
        1.0,
    )

    confidence_weight = smoothstep(
        tuning.min_assist_confidence,
        tuning.full_assist_confidence,
        threat.confidence,
    )
    assist_weight = (
        confidence_weight
        * threat.severity
        * (1.0 - threat.ambiguity * tuning.ambiguity_assist_penalty)
    )
    assist_weight = clamp(assist_weight, 0.0, 1.0)
    whisper_only = assist_weight <= 1e-9

    desired_scale = 1.0 - (1.0 - requested_scale) * assist_weight
    time_scale, cost, reserve_limited = _reserve_limited_scale(
        desired_scale=desired_scale,
        reserve=reserve,
        threat=threat,
        tuning=tuning,
    )

    real_window = threat.lead_seconds / time_scale
    usable_window = max(
        0.0,
        real_window
        - tuning.cue_latency_seconds
        - tuning.input_latency_seconds,
    )
    max_usable_window = max(
        0.0,
        threat.lead_seconds / tuning.min_time_scale
        - tuning.cue_latency_seconds
        - tuning.input_latency_seconds,
    )

    return SenseDecision(
        requested_time_scale=requested_scale,
        time_scale=time_scale,
        real_window_seconds=real_window,
        usable_response_seconds=usable_window,
        requested_decision_seconds=decision_budget,
        assist_weight=assist_weight,
        reserve_cost=cost,
        reserve_limited=reserve_limited,
        whisper_only=whisper_only,
        target_met=usable_window + 1e-9 >= decision_budget,
        unavoidable_at_minimum_scale=max_usable_window + 1e-9 < decision_budget,
    )


def estimate_success_rate(
    decision: SenseDecision,
    *,
    samples: int = 10_000,
    mean_choice_seconds: float = 0.72,
    choice_standard_deviation: float = 0.14,
    cue_accuracy: float = 0.95,
    seed: int = 7,
) -> float:
    """Estimate timing-and-interpretation success for a synthetic cohort.

    This is a tuning aid, not a model of any individual player. Production
    accessibility must use player-selected budgets rather than inferred traits.
    """

    if samples <= 0:
        raise ValueError("samples must be positive")
    if mean_choice_seconds <= 0 or choice_standard_deviation < 0:
        raise ValueError("reaction-time distribution is invalid")
    if not 0 <= cue_accuracy <= 1:
        raise ValueError("cue_accuracy must be in [0, 1]")

    generator = random.Random(seed)
    successes = 0
    for _ in range(samples):
        choice_time = max(
            0.05,
            generator.gauss(mean_choice_seconds, choice_standard_deviation),
        )
        in_time = choice_time <= decision.usable_response_seconds
        interpreted = generator.random() <= cue_accuracy
        successes += int(in_time and interpreted)
    return successes / samples


def default_matrix() -> Iterable[tuple[ThreatSignature, SenseDecision]]:
    tuning = SenseTuning()
    for lead in (0.15, 0.30, 0.60, 1.20, 2.40):
        for confidence in (0.40, 0.65, 0.90):
            threat = ThreatSignature(
                lead_seconds=lead,
                severity=0.85,
                confidence=confidence,
                ambiguity=0.15,
            )
            yield threat, evaluate_threat(threat, tuning=tuning)


def _print_matrix() -> None:
    print("lead  conf  scale  usable  cost  assist  target  mode")
    for threat, decision in default_matrix():
        mode = "whisper" if decision.whisper_only else "crown-flare"
        print(
            f"{threat.lead_seconds:>4.2f}  "
            f"{threat.confidence:>4.2f}  "
            f"{decision.time_scale:>5.2f}  "
            f"{decision.usable_response_seconds:>6.2f}  "
            f"{decision.reserve_cost:>4.1f}  "
            f"{decision.assist_weight:>6.2f}  "
            f"{str(decision.target_met):>6}  "
            f"{mode}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lead", type=float)
    parser.add_argument("--severity", type=float, default=0.85)
    parser.add_argument("--confidence", type=float, default=0.90)
    parser.add_argument("--ambiguity", type=float, default=0.10)
    parser.add_argument("--reserve", type=float, default=100.0)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if args.lead is None:
        _print_matrix()
        return

    threat = ThreatSignature(
        lead_seconds=args.lead,
        severity=args.severity,
        confidence=args.confidence,
        ambiguity=args.ambiguity,
    )
    decision = evaluate_threat(threat, reserve=args.reserve)
    payload = {
        "threat": {
            **asdict(threat),
            "family": threat.family.value,
            "channel": threat.channel.value,
        },
        "decision": asdict(decision),
        "estimated_success_rate": estimate_success_rate(decision),
    }
    if args.as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for key, value in payload["decision"].items():
            print(f"{key}: {value}")
        print(f"estimated_success_rate: {payload['estimated_success_rate']:.3f}")


if __name__ == "__main__":
    main()

