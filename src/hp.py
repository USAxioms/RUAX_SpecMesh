"""High-precision integer kernels at scale P = 10**90 (72 guard digits beyond WAD18).
Pure integer arithmetic. Constants are derived, not typed in."""
SCALE = 10 ** 18
P = 10 ** 90
K = P // SCALE
_ONE = 10 ** 100
_DROP = _ONE // P


def _atan_inv(n):
    x = _ONE // n
    n2 = n * n
    total = x
    k = 1
    while x:
        x //= n2
        term = x // (2 * k + 1)
        total += -term if k % 2 else term
        k += 1
    return total


def _atanh_inv(n):
    x = _ONE // n
    n2 = n * n
    total = x
    k = 1
    while x:
        x //= n2
        total += x // (2 * k + 1)
        k += 1
    return total


PI = (16 * _atan_inv(5) - 4 * _atan_inv(239)) // _DROP
HALF_PI = PI // 2
LN2 = (2 * _atanh_inv(3)) // _DROP
LN10 = (6 * _atanh_inv(3) + 2 * _atanh_inv(9)) // _DROP


def _series(r):
    neg = r < 0
    a = -r if neg else r
    a2 = a * a // P
    s = 0
    term = a
    n = 1
    sign = 1
    while term:
        s += sign * term
        term = term * a2 // P // ((n + 1) * (n + 2))
        n += 2
        sign = -sign
    c = 0
    term = P
    n = 0
    sign = 1
    while term:
        c += sign * term
        term = term * a2 // P // ((n + 1) * (n + 2))
        n += 2
        sign = -sign
    return (-s if neg else s), c


def sincos(t):
    """(sin, cos) of angle t (scale P), both at scale P."""
    k = (t + HALF_PI // 2) // HALF_PI
    s, c = _series(t - k * HALF_PI)
    q = k % 4
    if q == 0:
        return s, c
    if q == 1:
        return c, -s
    if q == 2:
        return -s, -c
    return -c, s


def ln(x):
    """Natural log of x > 0 (scale P) at scale P."""
    k = x.bit_length() - P.bit_length()
    m = x >> k if k >= 0 else x << (-k)
    if m < P:
        m <<= 1
        k -= 1
    z = (m - P) * P // (m + P)
    z2 = z * z // P
    term = z
    total = 0
    n = 1
    while term:
        total += term // n
        term = term * z2 // P
        n += 2
    return 2 * total + k * LN2
