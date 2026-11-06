import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from wad18 import *
import spectrum as S
import mathw as M

D = lambda s: from_decimal(s)[0]
FC, BW, GUARD = D("140000000000"), D("2160000000"), D("216000000")
LO, HI = D("130000000000"), D("150000000000")


class TestPlan(unittest.TestCase):
    def test_uniform_geometry(self):
        plan = S.plan_uniform(FC, 8, BW, GUARD)
        self.assertEqual(len(plan), 8)
        self.assertEqual(S.chan_bounds(*plan[0]), (D("130604000000"), D("132764000000")))
        self.assertEqual(S.chan_bounds(*plan[7]), (D("147236000000"), D("149396000000")))
        self.assertEqual(plan[0][0] + plan[7][0], 2 * FC)
        self.assertEqual(plan[3][0], D("138812000000"))
        self.assertEqual(S.plan_uniform(FC, 0, BW, GUARD), [])
        self.assertEqual(S.plan_uniform(FC, -3, BW, GUARD), [])
        self.assertEqual(S.plan_uniform(FC, 1, BW, GUARD), [(FC, BW)])

    def test_valid_plan_boundary_tight(self):
        plan = S.plan_uniform(FC, 8, BW, GUARD)
        lo0, hi0 = S.chan_bounds(*plan[0])
        lo1, _ = S.chan_bounds(*plan[1])
        self.assertEqual(hi0 + GUARD, lo1)
        self.assertEqual(S.validate_plan(plan, GUARD, LO, HI), (True, 0, []))
        self.assertEqual(S.validate_plan(list(reversed(plan)), GUARD, LO, HI), (True, 0, []))

    def test_one_ulp_violation(self):
        plan = S.plan_uniform(FC, 8, BW, GUARD)
        plan[1] = (plan[1][0] - 1, plan[1][1])
        ok, bleed, errs = S.validate_plan(plan, GUARD, LO, HI)
        self.assertEqual((ok, bleed, errs), (False, 1, [("GUARD_VIOLATION", 1)]))

    def test_band_edges(self):
        plan = S.plan_uniform(FC, 8, BW, GUARD)
        lo0, _ = S.chan_bounds(*plan[0])
        self.assertTrue(S.validate_plan(plan, GUARD, lo0, HI)[0])
        r = S.validate_plan(plan, GUARD, lo0 + 1, HI)
        self.assertEqual((r[0], r[2]), (False, [("OUT_OF_BAND", 0)]))
        _, hi7 = S.chan_bounds(*plan[7])
        self.assertTrue(S.validate_plan(plan, GUARD, LO, hi7)[0])
        r = S.validate_plan(plan, GUARD, LO, hi7 - 1)
        self.assertEqual((r[0], r[2]), (False, [("OUT_OF_BAND", 7)]))

    def test_bleed_sum_and_indices(self):
        chs = [(10, 20), (35, 20), (60, 20)]
        ok, bleed, errs = S.validate_plan(chs, 10, -100, 100)
        self.assertEqual((ok, bleed), (False, 10))
        self.assertEqual(errs, [("GUARD_VIOLATION", 1), ("GUARD_VIOLATION", 2)])
        ok, bleed, errs = S.validate_plan([(10, 20), (35, 20), (60, 20)], 5, -100, 100)
        self.assertEqual((ok, bleed, errs), (True, 0, []))

    def test_nested_and_duplicates(self):
        ok, bleed, errs = S.validate_plan([(0, 100), (0, 10)], 1, -1000, 1000)
        self.assertFalse(ok)
        self.assertGreater(bleed, 0)
        ok, bleed, errs = S.validate_plan([(FC, BW), (FC, BW)], GUARD, LO, HI)
        self.assertEqual((ok, bleed > 0), (False, True))
        far = S.validate_plan([(0, 100), (50, 20), (500, 10)], 1, -1000, 1000)
        self.assertEqual([e for e in far[2] if e[0] == "GUARD_VIOLATION"], [("GUARD_VIOLATION", 1)])

    def test_param_errors(self):
        self.assertEqual(S.validate_plan([], GUARD, LO, HI), (False, 0, [("EMPTY_PLAN", -1)]))
        r = S.validate_plan([(FC, BW)], -1, LO, HI)
        self.assertEqual((r[0], r[2]), (False, [("BAD_GUARD", -1)]))
        r = S.validate_plan([(FC, 0)], 0, LO, HI)
        self.assertEqual((r[0], r[2]), (False, [("BAD_BANDWIDTH", 0)]))
        r = S.validate_plan([(FC, -5)], 0, LO, HI)
        self.assertIn(("BAD_BANDWIDTH", 0), r[2])

    def test_one_ulp_bandwidth_ok(self):
        self.assertEqual(S.validate_plan([(FC, 1)], 0, LO, HI), (True, 0, []))

    def test_odd_bandwidth_widens(self):
        self.assertEqual(S.chan_bounds(5, 3), (4, 7))
        self.assertEqual(S.chan_bounds(5, 4), (3, 7))

    def test_saturation(self):
        r = S.validate_plan([(0, 4), (0, 4)], MAXV, -MAXV, MAXV)
        self.assertEqual(r[1], MAXV)


class TestMask(unittest.TestCase):
    def setUp(self):
        self.mask = S.make_mask(BW)

    def test_structure(self):
        self.assertEqual(self.mask, [(D("216000000"), -25 * WAD), (D("1080000000"), -35 * WAD), (MAXV, -45 * WAD)])
        self.assertEqual(S.mask_limit([], 5), MINV)

    def test_limits_at_boundaries(self):
        up1, up2 = D("216000000"), D("1080000000")
        self.assertEqual(S.mask_limit(self.mask, 0), -25 * WAD)
        self.assertEqual(S.mask_limit(self.mask, up1 - 1), -25 * WAD)
        self.assertEqual(S.mask_limit(self.mask, up1), -35 * WAD)
        self.assertEqual(S.mask_limit(self.mask, up2 - 1), -35 * WAD)
        self.assertEqual(S.mask_limit(self.mask, up2), -45 * WAD)
        self.assertEqual(S.mask_limit(self.mask, MAXV - 1), -45 * WAD)
        self.assertEqual(S.mask_limit(self.mask, MAXV), -45 * WAD)

    def test_check_mask(self):
        ok = [(0, -25 * WAD), (D("216000000"), -35 * WAD), (D("2000000000"), -45 * WAD)]
        self.assertEqual(S.check_mask(ok, self.mask), (True, []))
        bad = [(0, -25 * WAD + 1), (D("216000000"), -35 * WAD), (D("2000000000"), -45 * WAD + 1)]
        self.assertEqual(S.check_mask(bad, self.mask), (False, [0, 2]))
        self.assertEqual(S.check_mask([(-1, 5 * WAD)], self.mask), (True, []))
        self.assertEqual(S.check_mask([(0, 5 * WAD)], self.mask), (False, [0]))
        self.assertEqual(S.check_mask([], self.mask), (True, []))
        self.assertEqual(S.check_mask([(1, -100 * WAD)], []), (False, [0]))

    def test_leakage(self):
        self.assertEqual(S.leakage_dbc(0, WAD), MINV)
        self.assertEqual(S.leakage_dbc(-5, WAD), MINV)
        self.assertEqual(S.leakage_dbc(0, 0), MINV)
        self.assertEqual(S.leakage_dbc(1, 1), 0)
        self.assertEqual(S.leakage_dbc(5, 0), MAXV)
        self.assertEqual(S.leakage_dbc(5, -1), MAXV)
        self.assertEqual(S.leakage_dbc(WAD // 1000, WAD), -30 * WAD)
        self.assertEqual(S.leakage_dbc(WAD, WAD), 0)
        # ratio is rounded up (conservative): 1/3 -> ceil
        self.assertEqual(S.leakage_dbc(1, 3), M.db_power(333333333333333334))


if __name__ == "__main__":
    unittest.main()
