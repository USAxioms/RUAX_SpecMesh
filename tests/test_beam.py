import os, sys, hashlib, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fractions import Fraction as Fr
from wad18 import *
import beam as B
import mathw as M
import oracle as O

SCALE = 10 ** 18
T = M.TWO_PI_WAD
D = lambda s: from_decimal(s)[0]
PI = O.pi()


def oracle_table(theta, phi, ratio, nx=8, ny=8):
    st, _ = O.sincos(Fr(theta, SCALE))
    sf, cf = O.sincos(Fr(phi, SCALE))
    r = Fr(ratio, SCALE)
    out = []
    for m in range(nx):
        row = []
        for n in range(ny):
            x = -PI * r * (m * st * cf + n * st * sf)
            x -= 2 * PI * (x // (2 * PI))
            w = O.rnd(x)
            row.append(w - T if w >= T else w)
        out.append(row)
    return out


class TestPhase(unittest.TestCase):
    def test_zero_cases(self):
        z = [[0] * 8 for _ in range(8)]
        self.assertEqual(B.phase_table(0, 0), z)
        self.assertEqual(B.phase_table(0, D("1.1")), z)
        self.assertEqual(B.phase_table(D("0.5"), D("1.1"), 0), z)

    def test_endfire(self):
        t = B.phase_table(1570796326794896619, 0)
        pw = 3141592653589793238
        self.assertEqual([t[m][0] for m in range(8)], [0, pw, 0, pw, 0, pw, 0, pw])
        self.assertEqual([t[0][n] for n in range(8)], [0] * 8)
        q = B.quantize(t, 16)
        self.assertEqual([q[m][3] for m in range(4)], [0, 32768, 0, 32768])

    def test_matches_exact_oracle(self):
        for th in ("0.3", "1.0", "0.7853981633974483"):
            for ph in ("0", "0.9", "2.5", "5.9"):
                for ratio in (WAD, D("1.067")):
                    got = B.phase_table(D(th), D(ph), ratio)
                    self.assertEqual(got, oracle_table(D(th), D(ph), ratio), (th, ph, ratio))

    def test_shape_and_args(self):
        t = B.phase_table(D("0.4"), D("0.4"), WAD, 3, 5)
        self.assertEqual((len(t), len(t[0])), (3, 5))
        self.assertEqual(t, [row[:5] for row in B.phase_table(D("0.4"), D("0.4"))[:3]])
        self.assertEqual(B.phase_table(D("0.4"), D("0.4"), WAD, 0, 4), [])
        self.assertEqual(B.phase_table(D("0.4"), D("0.4"), WAD, 2, 0), [[], []])
        self.assertEqual(B.phase_table(D("0.4"), D("0.4"), WAD), B.phase_table(D("0.4"), D("0.4")))

    def test_deterministic_and_range(self):
        a = B.phase_table(D("0.61"), D("2.2"))
        self.assertEqual(a, B.phase_table(D("0.61"), D("2.2")))
        self.assertTrue(B.check_range(a))

    def test_quantize(self):
        t = [[0, T // 2, T - 1, T // 4]]
        self.assertEqual(B.quantize(t, 2), [[0, 2, 0, 1]])
        self.assertEqual(B.quantize(t, 6), [[0, 32, 0, 16]])
        self.assertEqual(B.quantize(t, 0), B.quantize(t, 1))
        self.assertEqual(B.quantize(t, -9), B.quantize(t, 1))
        self.assertEqual(B.quantize(t, 99), B.quantize(t, 32))
        self.assertEqual(B.quantize(t, 33), B.quantize(t, 32))
        self.assertEqual(B.quantize(t, 1), [[0, 1, 0, 0]])
        self.assertEqual(B.quantize([[T // 2]], 32), [[2 ** 31]])
        self.assertEqual(B.quantize([[T // 2]], 31), [[2 ** 30]])
        self.assertEqual(max(max(r) for r in B.quantize(t, 32)) < 2 ** 32, True)

    def test_word_wrap(self):
        k = B.K
        self.assertEqual(B._word(T * k), 0)
        self.assertEqual(B._word(T * k - 1), 0)
        self.assertEqual(B._word((T - 1) * k), T - 1)
        self.assertEqual(B._word(0), 0)
        self.assertEqual(B._word(5 * k), 5)

    def test_circ_and_digest(self):
        self.assertEqual(B.circ_dist(5, 5), 0)
        self.assertEqual(B.circ_dist(0, T - 1), 1)
        self.assertEqual(B.circ_dist(T - 1, 0), 1)
        self.assertEqual(B.circ_dist(10, 13), 3)
        self.assertEqual(B.circ_dist(0, T // 2), T // 2)
        z = [[0, 0], [0, 0]]
        self.assertEqual(B.digest(z), hashlib.sha256(b"0,0;0,0").hexdigest())
        self.assertEqual(B.digest([[1, 2, 3]]), hashlib.sha256(b"1,2,3").hexdigest())
        self.assertNotEqual(B.digest([[1, 2], [3, 4]]), B.digest([[1, 2], [3, 5]]))


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.th, self.ph = D("0.5235987755982988"), D("0.7853981633974483")
        self.t = B.phase_table(self.th, self.ph)

    def test_linearity_holds_on_grid(self):
        for th in ("0.1", "0.6", "1.0472", "1.5"):
            for ph in ("0", "0.3", "1.9", "3.0", "4.4", "6.0"):
                for r in (WAD, D("0.9"), D("1.07")):
                    self.assertTrue(B.check_linearity(B.phase_table(D(th), D(ph), r)), (th, ph, r))

    def test_linearity_tolerance_edges(self):
        t = [row[:] for row in self.t]
        t[3][4] = (t[3][4] + 1) % T
        self.assertTrue(B.check_linearity(t))
        t[3][4] = (t[3][4] + 1) % T
        self.assertFalse(B.check_linearity(t))
        self.assertTrue(B.check_linearity(t, tol=2))
        self.assertFalse(B.check_linearity([[0, 1], [0]]))
        self.assertTrue(B.check_linearity([[0, 5, 9]]))
        self.assertTrue(B.check_linearity([[0], [5], [9]]))
        self.assertFalse(B.check_linearity([[0, 5, 9], [3, 5, 9]]))
        self.assertTrue(B.check_linearity([]))
        self.assertTrue(B.check_linearity([[]]))

    def test_range(self):
        self.assertTrue(B.check_range([[0, T - 1]]))
        self.assertFalse(B.check_range([[0, T]]))
        self.assertFalse(B.check_range([[-1]]))
        self.assertTrue(B.check_range([]))

    def test_parity(self):
        self.assertTrue(B.check_parity(self.t, B.phase_table(self.th, self.ph)))
        u = [row[:] for row in self.t]
        u[7][7] += 1
        self.assertFalse(B.check_parity(u, self.t))

    def test_audit_pass(self):
        r = B.audit(self.t, self.th, self.ph)
        self.assertEqual((r["ok"], r["reasons"], r["action"]), (True, [], "PASS"))
        self.assertEqual(r["digest"], B.digest(self.t))
        r = B.audit(B.phase_table(self.th, self.ph, D("1.05"), 4, 4), self.th, self.ph, D("1.05"), 4, 4)
        self.assertTrue(r["ok"])

    def test_audit_isolation_reasons(self):
        u = [row[:] for row in self.t]
        u[5][2] = (u[5][2] + 1) % T
        r = B.audit(u, self.th, self.ph)
        self.assertEqual((r["ok"], r["reasons"], r["action"]), (False, ["PARITY_FAIL"], "ISOLATE_CHANNEL"))
        u[5][2] = (u[5][2] + 40) % T
        self.assertEqual(B.audit(u, self.th, self.ph)["reasons"], ["PARITY_FAIL", "LINEARITY_FAIL"])
        u = [row[:] for row in self.t]
        u[0][0] = T
        self.assertEqual(B.audit(u, self.th, self.ph)["reasons"], ["PARITY_FAIL", "RANGE_FAIL"])
        r = B.audit(self.t, self.th, self.ph, D("1.1"))
        self.assertEqual(r["reasons"][0], "PARITY_FAIL")

    def test_envelope_and_eirp(self):
        lim = D("1.0471975511965976")
        self.assertTrue(B.steering_ok(0, lim))
        self.assertTrue(B.steering_ok(lim, lim))
        self.assertFalse(B.steering_ok(lim + 1, lim))
        self.assertFalse(B.steering_ok(-1, lim))
        self.assertEqual(B.eirp_dbm(10 * WAD, 64), 10 * WAD + M.db_amplitude(64 * WAD))
        self.assertEqual(B.eirp_dbm(10 * WAD, 1), 10 * WAD)
        self.assertEqual(B.eirp_dbm(MAXV, 64), MAXV)


if __name__ == "__main__":
    unittest.main()
