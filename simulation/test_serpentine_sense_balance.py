import unittest

from serpentine_sense_balance import (
    SenseTuning,
    ThreatSignature,
    estimate_success_rate,
    evaluate_threat,
    smoothstep,
)


class SerpentineSenseBalanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tuning = SenseTuning()

    def test_long_lead_needs_no_dilation(self) -> None:
        decision = evaluate_threat(
            ThreatSignature(
                lead_seconds=2.0,
                severity=1.0,
                confidence=1.0,
            ),
            tuning=self.tuning,
        )
        self.assertEqual(decision.time_scale, 1.0)
        self.assertEqual(decision.reserve_cost, 0.0)
        self.assertTrue(decision.target_met)

    def test_high_confidence_short_lead_creates_target_window(self) -> None:
        decision = evaluate_threat(
            ThreatSignature(
                lead_seconds=0.30,
                severity=1.0,
                confidence=1.0,
            ),
            tuning=self.tuning,
        )
        self.assertAlmostEqual(decision.time_scale, 0.30 / 1.15, places=6)
        self.assertAlmostEqual(decision.usable_response_seconds, 0.90, places=6)
        self.assertTrue(decision.target_met)
        self.assertGreater(decision.reserve_cost, 0)

    def test_minimum_scale_marks_impossible_forecast(self) -> None:
        decision = evaluate_threat(
            ThreatSignature(
                lead_seconds=0.05,
                severity=1.0,
                confidence=1.0,
            ),
            tuning=self.tuning,
        )
        self.assertAlmostEqual(
            decision.time_scale,
            self.tuning.min_time_scale,
            places=12,
        )
        self.assertTrue(decision.unavoidable_at_minimum_scale)
        self.assertFalse(decision.target_met)

    def test_low_confidence_is_whisper_only(self) -> None:
        decision = evaluate_threat(
            ThreatSignature(
                lead_seconds=0.30,
                severity=1.0,
                confidence=0.30,
            ),
            tuning=self.tuning,
        )
        self.assertTrue(decision.whisper_only)
        self.assertEqual(decision.time_scale, 1.0)
        self.assertEqual(decision.reserve_cost, 0.0)

    def test_severity_monotonically_strengthens_assistance(self) -> None:
        low = evaluate_threat(
            ThreatSignature(0.30, severity=0.35, confidence=1.0),
            tuning=self.tuning,
        )
        high = evaluate_threat(
            ThreatSignature(0.30, severity=0.95, confidence=1.0),
            tuning=self.tuning,
        )
        self.assertLess(high.time_scale, low.time_scale)
        self.assertGreater(high.assist_weight, low.assist_weight)

    def test_empty_reserve_disables_dilation(self) -> None:
        decision = evaluate_threat(
            ThreatSignature(0.30, severity=1.0, confidence=1.0),
            reserve=0,
            tuning=self.tuning,
        )
        self.assertTrue(decision.reserve_limited)
        self.assertEqual(decision.time_scale, 1.0)
        self.assertEqual(decision.reserve_cost, 0.0)

    def test_partial_reserve_never_overspends(self) -> None:
        decision = evaluate_threat(
            ThreatSignature(0.30, severity=1.0, confidence=1.0),
            reserve=1.25,
            tuning=self.tuning,
        )
        self.assertTrue(decision.reserve_limited)
        self.assertLessEqual(decision.reserve_cost, 1.25 + 1e-8)
        self.assertGreater(decision.time_scale, decision.requested_time_scale)

    def test_ambiguity_weakens_assist_weight(self) -> None:
        clear = evaluate_threat(
            ThreatSignature(0.50, severity=0.9, confidence=0.9, ambiguity=0.0),
            tuning=self.tuning,
        )
        ambiguous = evaluate_threat(
            ThreatSignature(0.50, severity=0.9, confidence=0.9, ambiguity=1.0),
            tuning=self.tuning,
        )
        self.assertLess(ambiguous.assist_weight, clear.assist_weight)

    def test_success_estimate_is_seeded_and_bounded(self) -> None:
        decision = evaluate_threat(
            ThreatSignature(0.50, severity=1.0, confidence=1.0),
            tuning=self.tuning,
        )
        first = estimate_success_rate(decision, samples=1_000, seed=19)
        second = estimate_success_rate(decision, samples=1_000, seed=19)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first, 0)
        self.assertLessEqual(first, 1)

    def test_invalid_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ThreatSignature(-0.1, severity=1.0, confidence=1.0)
        with self.assertRaises(ValueError):
            ThreatSignature(0.1, severity=1.1, confidence=1.0)
        with self.assertRaises(ValueError):
            evaluate_threat(
                ThreatSignature(0.1, severity=1.0, confidence=1.0),
                reserve=-1,
            )
        with self.assertRaises(ValueError):
            smoothstep(1.0, 1.0, 0.5)


if __name__ == "__main__":
    unittest.main()
