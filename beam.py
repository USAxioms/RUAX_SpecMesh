"""UPA steering-phase engine (d = lambda/2 at f_c) and recompute-and-compare state auditor.
phase(m,n) = -pi * (f/f_c) * (m*sin(t)cos(p) + n*sin(t)sin(p)) mod 2pi, computed at 10^-90, rounded once."""
import hashlib
from wad18 import WAD, MAXV, sat, round_div
import hp
import mathw
from mathw import TWO_PI_WAD

K = hp.K
P = hp.P


def _word(x_p):
    w = round_div(x_p, K)
    return w - TWO_PI_WAD if w >= TWO_PI_WAD else w


def phase_table(theta, phi, f_ratio=WAD, nx=8, ny=8):
    st, _ = hp.sincos(theta * K)
    sf, cf = hp.sincos(phi * K)
    u = st * cf // P
    v = st * sf // P
    k = hp.PI * (f_ratio * K) // P
    du = k * u // P
    dv = k * v // P
    two = 2 * hp.PI
    return [[_word((-(m * du + n * dv)) % two) for n in range(ny)] for m in range(nx)]


def quantize(table, bits):
    q = 1 << min(max(bits, 1), 32)
    return [[round_div(w * q, TWO_PI_WAD) % q for w in row] for row in table]


def digest(table):
    body = ";".join(",".join(str(w) for w in row) for row in table)
    return hashlib.sha256(body.encode("ascii")).hexdigest()


def circ_dist(a, b):
    d = (a - b) % TWO_PI_WAD
    return min(d, TWO_PI_WAD - d)


def check_parity(table, ref):
    return table == ref


def check_range(table):
    return all(0 <= w < TWO_PI_WAD for row in table for w in row)


def check_linearity(table, tol=1):
    if not table or not table[0]:
        return True
    if any(len(r) != len(table[0]) for r in table):
        return False
    for m in range(len(table)):
        for n in range(len(table[0])):
            expect = (table[m][0] + table[0][n]) % TWO_PI_WAD
            if circ_dist(table[m][n], expect) > tol:
                return False
    return True


def audit(table, theta, phi, f_ratio=WAD, nx=8, ny=8):
    ref = phase_table(theta, phi, f_ratio, nx, ny)
    reasons = []
    if not check_parity(table, ref):
        reasons.append("PARITY_FAIL")
    if not check_range(table):
        reasons.append("RANGE_FAIL")
    if not check_linearity(table):
        reasons.append("LINEARITY_FAIL")
    return {"ok": len(reasons) == 0, "reasons": reasons, "digest": digest(table),
            "action": "PASS" if not reasons else "ISOLATE_CHANNEL"}


def steering_ok(theta, theta_max):
    return 0 <= theta <= theta_max


def eirp_dbm(p_elem_dbm, n_elems):
    return sat(p_elem_dbm + mathw.db_amplitude(n_elems * WAD))
