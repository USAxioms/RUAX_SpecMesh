"""Independent exact-rational oracles (fractions.Fraction); share no code with src/."""
from fractions import Fraction as Fr

SCALE = 10 ** 18


def rnd(q):
    return (2 * q.numerator * SCALE + q.denominator) // (2 * q.denominator)


def sincos(x):
    s = Fr(0); c = Fr(0); t = Fr(1)
    for n in range(80):
        r = n % 4
        if r == 0: c += t
        elif r == 1: s += t
        elif r == 2: c -= t
        else: s -= t
        t = t * x / (n + 1)
    return s, c


def pi():
    def at(n):
        return sum(Fr((-1) ** k, (2 * k + 1) * n ** (2 * k + 1)) for k in range(50))
    return 16 * at(5) - 4 * at(239)


def ln(x):
    z = (x - 1) / (x + 1)
    return 2 * sum(z ** (2 * k + 1) / (2 * k + 1) for k in range(90))
