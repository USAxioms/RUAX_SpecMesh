"""Deterministic demo (PLACEHOLDER parameters). Output must be byte-identical on every platform."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from wad18 import WAD, from_decimal, to_decimal, round_div
import mathw as M
import spectrum as S
import beam as B

D = lambda s: from_decimal(s)[0]
FC, BW, GUARD = D("140000000000"), D("2160000000"), D("216000000")
BAND_LO, BAND_HI = D("130000000000"), D("150000000000")
THETA_MAX = M.deg_to_rad(D("60"))


def main():
    o = []
    o.append("[constants]")
    o.append("  pi=%s" % to_decimal(M.PI_WAD))
    o.append("  sin(30deg)=%s cos(30deg)=%s" % (to_decimal(M.sin_wad(M.deg_to_rad(D("30")))), to_decimal(M.cos_wad(M.deg_to_rad(D("30"))))))
    o.append("  10log10(2)=%s 20log10(64)=%s" % (to_decimal(M.db_power(D("2"))), to_decimal(M.db_amplitude(D("64")))))

    plan = S.plan_uniform(FC, 8, BW, GUARD)
    ok, bleed, errs = S.validate_plan(plan, GUARD, BAND_LO, BAND_HI)
    o.append("[channel plan] ok=%s bleed=%s errors=%s" % (ok, to_decimal(bleed), errs))
    for i, (c, bw) in enumerate(plan):
        lo, hi = S.chan_bounds(c, bw)
        o.append("  ch%d lo=%s hi=%s" % (i, to_decimal(lo), to_decimal(hi)))
    bad = list(plan)
    bad[4] = (bad[4][0] - D("100000000"), bad[4][1])
    ok, bleed, errs = S.validate_plan(bad, GUARD, BAND_LO, BAND_HI)
    o.append("[shifted ch4 by -100 MHz] ok=%s bleed=%s errors=%s" % (ok, to_decimal(bleed), errs))

    mask = S.make_mask(BW)
    samples = [(0, D("-26")), (D("216000000"), D("-36")), (D("2000000000"), D("-46"))]
    o.append("[mask] pass=%s" % (S.check_mask(samples, mask),))
    samples[1] = (D("216000000"), D("-34"))
    o.append("[mask] pass=%s (one sample 1 dB over limit)" % (S.check_mask(samples, mask),))
    o.append("[leakage] p_oob/p_in=1e-4 -> %s dBc" % to_decimal(S.leakage_dbc(D("0.0001"), WAD)))

    th, ph = M.deg_to_rad(D("30")), M.deg_to_rad(D("45"))
    o.append("[beam] theta=%s phi=%s steering_ok=%s" % (to_decimal(th), to_decimal(ph), B.steering_ok(th, THETA_MAX)))
    for i in (0, 3, 7):
        ratio = round_div(plan[i][0] * WAD, FC)
        t = B.phase_table(th, ph, ratio)
        a = B.audit(t, th, ph, ratio)
        o.append("  ch%d f_ratio=%s digest=%s action=%s" % (i, to_decimal(ratio), a["digest"][:16], a["action"]))
    ratio = round_div(plan[3][0] * WAD, FC)
    t = B.phase_table(th, ph, ratio)
    o.append("  ch3 word[1][0]=%s word[7][7]=%s" % (to_decimal(t[1][0]), to_decimal(t[7][7])))
    for row in B.quantize(t, 16):
        o.append("  " + " ".join("%5d" % c for c in row))
    t[2][5] = (t[2][5] + 3) % M.TWO_PI_WAD
    a = B.audit(t, th, ph, ratio)
    o.append("  tampered ch3: reasons=%s action=%s" % (a["reasons"], a["action"]))
    e = B.eirp_dbm(D("10"), 64)
    o.append("[eirp] 10 dBm/element x64 coherent = %s dBm" % to_decimal(e))
    return "\n".join(o) + "\n"


if __name__ == "__main__":
    sys.stdout.write(main())
