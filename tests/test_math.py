import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fractions import Fraction as Fr
from wad18 import *
SCALE = 10 ** 18
import hp, mathw as M
import oracle as O

W = from_int
D = lambda s: from_decimal(s)[0]


class TestConstants(unittest.TestCase):
    def test_pi_ln(self):
        self.assertEqual(hp.PI // 10 ** 10, int("3" + "14159265358979323846264338327950288419716939937510582097494459230781640628620899"))
        self.assertEqual(hp.LN2 // 10 ** 50, int("6931471805599453094172321214581765680755"))
        self.assertEqual(hp.LN10 // 10 ** 50, int("23025850929940456840179914546843642076011"))
        self.assertEqual(hp.P, 10 ** 90)
        self.assertEqual(hp.K, 10 ** 72)
        self.assertEqual(hp.HALF_PI, hp.PI // 2)
        self.assertEqual(M.PI_WAD, 3141592653589793238)
        self.assertEqual(M.TWO_PI_WAD, 6283185307179586477)

    def test_pi_independent(self):
        self.assertEqual(O.rnd(O.pi()), M.PI_WAD)
        self.assertEqual(O.rnd(2 * O.pi()), M.TWO_PI_WAD)


class TestTrig(unittest.TestCase):
    def test_known(self):
        self.assertEqual((M.sin_wad(0), M.cos_wad(0)), (0, WAD))
        self.assertEqual(M.sin_wad(1570796326794896619), WAD)
        self.assertEqual(M.cos_wad(1570796326794896619), 0)
        self.assertEqual(M.sin_wad(523598775598298873), 500000000000000000)
        self.assertEqual(M.cos_wad(523598775598298873), 866025403784438647)
        self.assertEqual(M.sin_wad(M.PI_WAD), 0)
        self.assertEqual(M.cos_wad(M.PI_WAD), -WAD)
        self.assertEqual(M.sin_wad(-523598775598298873), -500000000000000000)
        self.assertEqual(M.deg_to_rad(W(180)), M.PI_WAD)
        self.assertEqual(M.deg_to_rad(W(30)), 523598775598298873)
        self.assertEqual(M.deg_to_rad(-W(90)), -1570796326794896619)

    def test_correctly_rounded_vs_oracle(self):
        angles = ["0.1", "0.7", "1.3", "1.9", "2.6", "3.3", "4.4", "5.9", "-0.4", "-2.2", "-3.9", "6.28", "0.000000000000000001"]
        for a in angles:
            w = D(a)
            s, c = O.sincos(Fr(w, SCALE))
            self.assertEqual(M.sin_wad(w), O.rnd(s), a)
            self.assertEqual(M.cos_wad(w), O.rnd(c), a)

    def test_quadrants_and_identity(self):
        for i in range(-14, 15):
            w = i * 450000000000000000
            s, c = M.sin_wad(w), M.cos_wad(w)
            self.assertLessEqual(abs(s * s + c * c - W(1) * WAD), 4 * WAD)
            self.assertEqual(M.sin_wad(w + M.TWO_PI_WAD) - s in (-2, -1, 0, 1, 2), True)

    def test_total_large(self):
        for x in (MAXV, MINV, 10 ** 30):
            self.assertTrue(-WAD <= M.sin_wad(x) <= WAD)
            self.assertTrue(-WAD <= M.cos_wad(x) <= WAD)
        self.assertLess(abs(hp.sincos(hp.PI)[0]), 10 ** 30)


class TestLog(unittest.TestCase):
    def test_known(self):
        self.assertEqual(M.ln_wad(WAD), 0)
        self.assertEqual(M.log10_wad(W(10)), WAD)
        self.assertEqual(M.log10_wad(W(100)), W(2))
        self.assertEqual(M.log10_wad(WAD // 10), -WAD)
        self.assertEqual(M.db_power(W(2)), 3010299956639811952)
        self.assertEqual(M.db_amplitude(W(2)), 6020599913279623904)
        self.assertEqual(M.db_power(W(10)), W(10))
        self.assertEqual(M.db_amplitude(W(10)), W(20))
        self.assertEqual(M.db_power(WAD // 1000), -W(30))
        self.assertEqual(M.db_power(WAD), 0)
        self.assertEqual(M.ln_wad(W(2)), 693147180559945309)

    def test_vs_oracle(self):
        for a in ["0.5", "0.77", "1.0000000000000001", "1.3", "1.99", "2"]:
            w = D(a)
            q = O.ln(Fr(w, SCALE))
            self.assertEqual(M.ln_wad(w), O.rnd(q), a)

    def test_large_small_reduction(self):
        for k in (-5, -1, 1, 7, 60):
            w = W(1) * 2 ** k if k >= 0 else WAD // 2 ** (-k)
            self.assertEqual(M.ln_wad(w), O.rnd(k * O.ln(Fr(2))), k)
        self.assertEqual(M.ln_wad(1), O.rnd(-18 * (3 * O.ln(Fr(2)) + O.ln(Fr(5, 4)))))

    def test_additivity(self):
        for a, b in ((3, 7), (11, 13), (2, 5)):
            lhs = M.log10_wad(W(a * b))
            rhs = M.log10_wad(W(a)) + M.log10_wad(W(b))
            self.assertLessEqual(abs(lhs - rhs), 2)

    def test_one_ulp_arguments(self):
        self.assertEqual(M.ln_wad(1), O.rnd(-18 * (3 * O.ln(Fr(2)) + O.ln(Fr(5, 4)))))
        self.assertEqual(M.log10_wad(1), -18 * WAD)
        self.assertEqual(M.db_power(1), -180 * WAD)
        self.assertEqual(M.db_amplitude(1), -360 * WAD)

    def test_totality(self):
        for x in (0, -1, MINV):
            self.assertEqual(M.ln_wad(x), MINV)
            self.assertEqual(M.log10_wad(x), MINV)
            self.assertEqual(M.db_power(x), MINV)
            self.assertEqual(M.db_amplitude(x), MINV)
        self.assertGreater(M.db_power(MAXV), 0)

    def test_db_64(self):
        self.assertLessEqual(abs(M.db_amplitude(W(64)) - 6 * M.db_amplitude(W(2))), 6)
        self.assertEqual(M.db_amplitude(W(64)) // 10 ** 12, 36123599)


if __name__ == "__main__":
    unittest.main()
