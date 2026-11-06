"""Channel-plan validator and stepped spectral mask. PLACEHOLDER mask values (not verbatim ITU/FCC)."""
from wad18 import WAD, MAXV, MINV, sat, mul_down, div_up
import mathw

TIERS = ((100000000000000000, -25 * WAD), (500000000000000000, -35 * WAD))
FINAL_LIMIT = -45 * WAD


def chan_bounds(center, bw):
    half = bw // 2
    return center - half, center + (bw - half)


def plan_uniform(fc, n, bw, guard):
    pitch = bw + guard
    return [(fc + ((2 * i - (n - 1)) * pitch) // 2, bw) for i in range(n)]


def validate_plan(chs, guard, band_lo, band_hi):
    """Returns (ok, bleed, errors). bleed = sum over ordered channel pairs of guard shortfall (exact integer)."""
    if not chs:
        return (False, 0, [("EMPTY_PLAN", -1)])
    errors = []
    if guard < 0:
        errors.append(("BAD_GUARD", -1))
    order = sorted(range(len(chs)), key=lambda i: (chs[i][0], i))
    bounds = []
    for i in order:
        c, bw = chs[i]
        if bw <= 0:
            errors.append(("BAD_BANDWIDTH", i))
        lo, hi = chan_bounds(c, bw)
        if lo < band_lo or hi > band_hi:
            errors.append(("OUT_OF_BAND", i))
        bounds.append((i, lo, hi))
    bleed = 0
    for a in range(len(bounds)):
        for b in range(a + 1, len(bounds)):
            short = bounds[a][2] + guard - bounds[b][1]
            if short > 0:
                bleed += short
                errors.append(("GUARD_VIOLATION", bounds[b][0]))
    return (len(errors) == 0, sat(bleed), errors)


def make_mask(bw):
    return [(mul_down(bw, f), lim) for f, lim in TIERS] + [(MAXV, FINAL_LIMIT)]


def mask_limit(mask, offset):
    if not mask:
        return MINV
    for upper, lim in mask:
        if offset < upper:
            return lim
    return mask[-1][1]


def check_mask(samples, mask):
    """samples: (offset_from_occupied_edge, level_dBc). Negative offset = in band (not mask-governed)."""
    bad = []
    for i, (off, level) in enumerate(samples):
        if off < 0:
            continue
        if level > mask_limit(mask, off):
            bad.append(i)
    return (len(bad) == 0, bad)


def leakage_dbc(p_oob, p_ref):
    if p_oob <= 0:
        return MINV
    if p_ref <= 0:
        return MAXV
    return mathw.db_power(div_up(p_oob, p_ref))
