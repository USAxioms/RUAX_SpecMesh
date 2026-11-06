"""WAD18 transcendental functions: results are the 10^-18 rounding of a 10^-90 computation
(error <= 0.5 ulp + ~1e-50 ulp, hence < 1 ulp). Total: non-positive log arguments saturate to MINV."""
from wad18 import WAD, MINV, sat, clamp, round_div
import hp

K = hp.K
PI_WAD = round_div(hp.PI, K)
TWO_PI_WAD = round_div(2 * hp.PI, K)


def sin_wad(t):
    s, _ = hp.sincos(t * K)
    return clamp(round_div(s, K), -WAD, WAD)


def cos_wad(t):
    _, c = hp.sincos(t * K)
    return clamp(round_div(c, K), -WAD, WAD)


def ln_wad(x):
    if x <= 0:
        return MINV
    return sat(round_div(hp.ln(x * K), K))


def _scaled_log10(x, factor):
    if x <= 0:
        return MINV
    return sat(round_div(hp.ln(x * K) * factor * hp.P // hp.LN10, K))


def log10_wad(x):
    return _scaled_log10(x, 1)


def db_power(ratio):
    return _scaled_log10(ratio, 10)


def db_amplitude(ratio):
    return _scaled_log10(ratio, 20)


def deg_to_rad(d):
    return sat(round_div(d * hp.PI, 180 * hp.P))
