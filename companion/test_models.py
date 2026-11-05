import math
import unittest
import models as m
from calculations import radius
from metrics import lower


class ModelTests(unittest.TestCase):
    def test_horizon_and_markov(self):
        self.assertAlmostEqual(m.horizon_success(.98, 8), .8508, 4)
        self.assertAlmostEqual(m.finite_horizon([[.2]], [.72], [1], 3), .8928)
        self.assertAlmostEqual(m.finite_horizon([[.2]], [.72], [1], 400), .9)

    def test_two_step_dependence_bounds(self):
        self.assertAlmostEqual(m.two_step_joint(.95, .95, 0), .9025)
        self.assertAlmostEqual(m.two_step_joint(.95, .95, 1), .95)
        lo, hi = m.two_step_rho_range(.95, .95)
        self.assertAlmostEqual(m.two_step_joint(.95, .95, lo), .90)
        self.assertAlmostEqual(hi, 1.0)

    def test_two_step_feasible_correlation(self):
        lo, hi = m.two_step_rho_range(.90, .95)
        self.assertAlmostEqual(lo, -0.0765, places=4)
        self.assertAlmostEqual(hi, 0.6882, places=4)
        self.assertAlmostEqual(m.two_step_joint(.90, .95, hi), .90)
        self.assertAlmostEqual(m.two_step_joint(.90, .95, lo), .85)

    def test_two_step_rejects_impossible_correlation(self):
        with self.assertRaises(ValueError):
            m.two_step_joint(.90, .95, 0.9)
        with self.assertRaises(ValueError):
            m.two_step_joint(.95, .95, -0.5)

    def test_incident_controls(self):
        r = m.IncidentRecord("policy rev 5", "summary without revision",
                             ["A->B"], ["handoff check", "commit check"],
                             "duplicate write")
        self.assertEqual(len(r.controls()), 2)

    def test_sample_size(self):
        n = m.required_n(.96, .95)
        self.assertEqual(n, 1237)
        self.assertGreaterEqual(lower(round(.96 * n), n), .95)
        # no smaller n qualifies (the V6 search skipped 1,237 and returned 1,260)
        self.assertFalse(any(lower(round(.96 * k), k) >= .95 for k in range(1, n)))
        self.assertIsNone(m.required_n(.95, .95))

    def test_sample_size_sawtooth_and_stable(self):
        self.assertFalse(m.qualifies(.96, .95, 1238))
        self.assertTrue(m.qualifies(.96, .95, 1260))
        s = m.required_n(.96, .95, stable=True)
        self.assertEqual(s, 1415)
        self.assertTrue(all(m.qualifies(.96, .95, k) for k in range(s, 2 * s + 1)))

    def test_tail(self):
        self.assertEqual(m.zero_event_n(.001), 2995)
        self.assertAlmostEqual(
            m.cvar([(.98, 0), (.015, 10), (.005, 100)], .99), 55)

    def test_transitions(self):
        self.assertEqual(m.advance("planned", "preparing", 3, 3),
                         ("preparing", 4))
        with self.assertRaises(ValueError):
            m.advance("planned", "accepted", 3, 3)
        with self.assertRaises(ValueError):
            m.advance("planned", "preparing", 2, 3)

    def test_duplicates(self):
        self.assertEqual(m.expected_duplicates(.1, 3, True), 0)
        self.assertAlmostEqual(m.expected_duplicates(.1, 3, False), .111)

    def test_stall(self):
        h = [{"milestones": 2, "action": "search"}] * 4
        self.assertTrue(m.stalled(h))
        h2 = [{"milestones": i, "action": "a"} for i in range(4)]
        self.assertFalse(m.stalled(h2))

    def test_envelope_and_scope(self):
        e = m.SourceEnvelope("policy", 5, "approved-policy", "t", 0, None)
        ok = dict(tenant="t", now=3, head_revision=5,
                  required_authority="approved-policy")
        self.assertTrue(m.eligible(e, **ok))
        self.assertFalse(m.eligible(e, **dict(ok, head_revision=6)))
        s = m.effective_scope({"read", "write"}, {"write"},
                              {"write", "delete"}, {"write"})
        self.assertEqual(s, {"write"})
        self.assertFalse(m.permitted("write", s, {"write"}))

    def test_radius_fix_on_cycle(self):
        A = [[0, .5, 0, .9], [.9, 0, 0, 0], [0, .9, 0, .5], [0, 0, .9, 0]]
        self.assertAlmostEqual(m.spectral_radius(A), 1.1225, 4)
        self.assertAlmostEqual(radius(A), 1.1225, 4)
        self.assertAlmostEqual(radius([[0, 1], [1, 0]]), 1.0, 6)
        self.assertAlmostEqual(
            m.spectral_radius([[.2, 0, .4], [.3, .2, 0], [0, .3, .2]]),
            .5302, 4)

    def test_radius_upper_is_conservative(self):
        counts = [[None, (30, 100)], [(25, 100), None]]
        est = m.spectral_radius([[0, .30], [.25, 0]])
        self.assertGreater(m.radius_upper(counts), est)

    # ---- V8: spectral-radius enclosure (release blocker) -------------
    def test_radius_counterexample_is_not_below_one(self):
        A = [[1.0, 0.0, 0.0], [0.0, 0.999, 1.0], [0.0, 0.0, 0.999]]
        b = m.radius_bracket(A)
        self.assertLessEqual(b.lower, 1.0)
        self.assertGreaterEqual(b.upper, 1.0)
        self.assertAlmostEqual(m.spectral_radius(A), 1.0, 9)
        self.assertNotEqual(m.decay_verdict(b), 'decays')

    def test_radius_upper_fixture_does_not_certify_decay(self):
        counts = [[(1, 1), None, None],
                  [None, (9980, 10000), (1, 1)],
                  [None, None, (9980, 10000)]]
        U = m.upper_matrix(counts)
        self.assertAlmostEqual(U[1][1], 0.9988657362, 8)
        self.assertEqual(U[1][2], 1.0)
        b = m.radius_bracket(U)          # what radius_upper returns as .upper
        self.assertGreaterEqual(b.upper, 1.0)
        self.assertNotEqual(m.decay_verdict(b), 'decays')

    def test_radius_special_matrices(self):
        self.assertEqual(m.spectral_radius([[0, 0], [0, 0]]), 0.0)
        self.assertAlmostEqual(m.spectral_radius([[.3, 0, 0], [0, .7, 0], [0, 0, .2]]), .7, 10)
        self.assertAlmostEqual(m.spectral_radius([[0, .9], [.4, 0]]), .6, 10)
        self.assertAlmostEqual(m.spectral_radius([[0, 0, .8], [.5, 0, 0], [0, .2, 0]]),
                               (.08) ** (1 / 3), 10)
        self.assertAlmostEqual(m.spectral_radius([[.5, 0], [.7, .2]]), .5, 10)

    def test_radius_nearly_critical(self):
        b = m.radius_bracket([[0, .999998], [1.0, 0]])
        self.assertTrue(b.converged)
        self.assertLess(b.upper, 1.0)
        self.assertEqual(m.decay_verdict(b), 'decays')
        b = m.radius_bracket([[0, 1.0], [1.0, 0]])
        self.assertEqual(m.decay_verdict(b), 'inconclusive')
        self.assertEqual(m.decay_verdict(m.radius_bracket([[1.2]])), 'grows')

    def test_radius_unknown_edges_stay_unknown(self):
        known = [[(10, 100), None], [(5, 100), None]]
        unknown = [[(10, 100), m.UNKNOWN], [(5, 100), None]]
        self.assertGreater(m.radius_upper(unknown), m.radius_upper(known))
        self.assertEqual(m.upper_matrix(unknown)[0][1], 1.0)

    def test_radius_rejects_invalid_input(self):
        for bad in ([], [[1, 2]], [[-0.1]], [[float('nan')]], [[True]],
                    [[1, 0], [0]], 'matrix'):
            with self.assertRaises(ValueError):
                m.radius_bracket(bad)
        for bad in ([[(5, 3)]], [[(1, 0)]], [[(1.0, 2)]], [[(1, 2, 3)]], [[]]):
            with self.assertRaises(ValueError):
                m.upper_matrix(bad)

    def test_radius_matches_independent_eigensolver(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest('numpy not installed; enclosure tests still run')
        import random
        rng = random.Random(7)
        for n in (2, 3, 4, 6):
            for _ in range(25):
                A = [[rng.random() * (rng.random() < .6) for _ in range(n)]
                     for _ in range(n)]
                ref = max(abs(np.linalg.eigvals(np.array(A))))
                b = m.radius_bracket(A)
                self.assertLessEqual(b.lower, ref + 1e-9)
                self.assertGreaterEqual(b.upper, ref - 1e-9)
                self.assertAlmostEqual(m.spectral_radius(A), ref, 7)

    def test_radius_teaching_values_retained(self):
        A = [[.2, 0, .4], [.3, .2, 0], [0, .3, .2]]
        self.assertAlmostEqual(m.spectral_radius(A), .5302, 4)
        self.assertAlmostEqual(m.spectral_radius([[2 * x for x in r] for r in A]), 1.0604, 4)

    def test_joint_and_redundancy(self):
        lo, hi = m.joint_interval([.97, .97, .98, .99])
        self.assertAlmostEqual(lo, .91)
        self.assertEqual(hi, .97)
        self.assertAlmostEqual(m.redundant_miss(.2, .5), .12)

    def test_evaluator(self):
        obs = m.observed_positive(.8, .95, .90)
        self.assertAlmostEqual(obs, .78)
        self.assertAlmostEqual(m.corrected_rate(obs, .95, .90), .8)
        with self.assertRaises(ValueError):
            m.corrected_rate(.5, .5, .5)

    def test_mcnemar(self):
        self.assertAlmostEqual(m.mcnemar_exact(5, 1), .21875)
        self.assertEqual(m.mcnemar_exact(0, 0), 1.0)

    def test_manifest_changes_with_content(self):
        a = m.manifest({"tasks.json": b"1"})["root"]
        b = m.manifest({"tasks.json": b"2"})["root"]
        self.assertNotEqual(a, b)

    def test_false_completion(self):
        E = m.MissionEvent
        ev = [E("m", 1, "commit", "C", "tools", operation="op-1"),
              E("m", 2, "claim_complete", "C", "verify", operation="op-1")]
        self.assertTrue(m.false_completion(ev))
        ev.append(E("m", 3, "verify_state", "V", "verify", operation="op-1", passed=True))
        self.assertFalse(m.false_completion(ev))

    def test_false_completion_needs_same_mission_operation_and_pass(self):
        E = m.MissionEvent
        claim = E("m", 2, "claim_complete", "C", "verify", operation="op-1")
        other_mission = E("n", 3, "verify_state", "V", "verify", operation="op-1", passed=True)
        other_op = E("m", 4, "verify_state", "V", "verify", operation="op-2", passed=True)
        failed = E("m", 5, "verify_state", "V", "verify", operation="op-1", passed=False)
        self.assertEqual(m.false_completion([claim, other_mission, other_op, failed]), [claim])
        second = E("m", 6, "claim_complete", "C", "verify", operation="op-3")
        ok = E("m", 7, "verify_state", "V", "verify", operation="op-1", passed=True)
        self.assertEqual(m.false_completion([claim, second, ok]), [second])

    def test_coverage_risk_unknown_and_lengths(self):
        cov, risk = m.coverage_risk([.2, .3], [1, 0], .9)
        self.assertEqual(cov, 0.0); self.assertIsNone(risk)
        with self.assertRaises(ValueError):
            m.coverage_risk([.9, .8], [1], .5)
        with self.assertRaises(ValueError):
            m.brier([.9], [1, 0])

    def test_radius_sensitivity_ranking(self):
        A = [[.2, 0, .4], [.3, .2, 0], [0, .3, .2]]
        s = m.radius_sensitivity(A)
        self.assertGreater(s[(1, 0)], s[(0, 2)])   # edge 1->2 beats the larger edge 3->1

    def test_slo_and_mix(self):
        self.assertAlmostEqual(m.burn_rate(80, 5000, .99), 1.6)
        self.assertAlmostEqual(
            m.standardized({"r": .98, "e": .80}, {"r": .9, "e": .1}), .962)

    def test_canary_queue(self):
        self.assertEqual(m.canary_n(.01), 299)
        q = m.mm1(10, 12)
        self.assertAlmostEqual(q["W_min"], 30)
        self.assertAlmostEqual(q["Wq_min"], 25)

    def test_subgroup_floor(self):
        r = m.subgroup_check({"a": (980, 1000), "b": (40, 50)},
                             {"a": .95, "b": .90})
        self.assertTrue(r["a"]["passes"])
        self.assertFalse(r["b"]["passes"])

    def test_value_and_debt(self):
        self.assertAlmostEqual(
            m.incremental_value(10000, .85, .90, 10, 0, .2, I=1000), 2000)
        self.assertEqual(m.debt_queue(10, 5, 5)[-1], 0)
        self.assertGreater(m.debt_queue(10, 5, 4)[-1], 0)

    def test_envelope_membership(self):
        e = ("address", "low")
        self.assertTrue(m.supported(e, {e: 1}, {e: 1}, {e: 1}))
        self.assertFalse(m.supported(e, {e: 1}, {e: 0}, {e: 1}))

    # ---- V7 additions
    def test_min_budget(self):
        self.assertEqual(m.min_budget(.7, 5, .95), 10)
        self.assertEqual(m.min_budget(.5, 5, .99), 19)

    def test_budget_consumed(self):
        self.assertAlmostEqual(m.budget_consumed(14.4, 1, 720), .02)
        self.assertAlmostEqual(m.budget_consumed(6, 6, 720), .05)

    def test_sojourn_exceeds(self):
        self.assertAlmostEqual(m.sojourn_exceeds(10, 12, 1), math.exp(-2))
        with self.assertRaises(ValueError):
            m.sojourn_exceeds(12, 12, 1)

    def test_affected_missions(self):
        self.assertAlmostEqual(m.affected_missions(40, 20, 15), 40 * 35 / 60)

    def test_reproduction_gap_symmetry_and_monotone(self):
        a = m.reproduction_gap(.9, 100, 5); b = m.reproduction_gap(.9, 400, 5)
        self.assertGreater(a, b)
        self.assertAlmostEqual(m.reproduction_gap(.9, 50, 0), 1.0)

    def test_reconstructed_rate(self):
        self.assertAlmostEqual(m.reconstructed_rate(970, 1000, 80, 60), 890 / 1060)

    def test_labour_margin_and_break_even(self):
        self.assertAlmostEqual(m.labour_margin(12, 20, 60), -8)
        self.assertAlmostEqual(m.labour_margin(12, 3, 60), 9)
        self.assertAlmostEqual(m.break_even_acceptance(2, .2, 3, 8), .325)


if __name__ == "__main__":
    unittest.main()
