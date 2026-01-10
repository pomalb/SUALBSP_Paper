from __future__ import annotations

from dataclasses import dataclass

from .instance import Instance


def ceil_div(num: int, den: int) -> int:
    return (num + den - 1) // den


def lm1(instance: Instance) -> int:
    return ceil_div(sum(instance.t), instance.c)


def lms1(instance: Instance) -> int:
    if instance.setup_directed:
        return lms1_fb(instance)
    return lms1_f(instance)


def lms1_fb(instance: Instance) -> int:
    tsum = sum(instance.t)
    n = instance.n
    m = ceil_div(tsum, instance.c)

    sfi = instance.sfi or [instance.c] * n
    sbi = instance.sbi or [instance.c] * n

    ta_sum = sum(sfi[: max(0, n - m)])
    mu_sum = sum(sbi[: max(0, m)])
    total_capacity = instance.c * m

    while tsum + ta_sum + mu_sum > total_capacity:
        if n - m - 1 >= 0:
            ta_sum -= sfi[n - m - 1]
        total_capacity += instance.c
        if m < n:
            mu_sum += sbi[m]
        m += 1
    return m


def lms1_f(instance: Instance) -> int:
    tsum = sum(instance.t)
    n = instance.n
    m = ceil_div(tsum, instance.c)
    if m == n:
        return m

    sfi = instance.sfi or [instance.c] * n
    ta_sum = sum(sfi[: n + 1 - m])
    total_capacity = instance.c * m
    while tsum + ta_sum > total_capacity:
        ta_sum -= sfi[n - m]
        m += 1
        total_capacity += instance.c
    return m


def lm2(instance: Instance) -> int:
    count = 0
    count_mid = 0
    for t in instance.t:
        if t * 2 > instance.c:
            count += 1
        elif t * 2 == instance.c:
            count_mid += 1
    return count + (count_mid + 1) // 2


def lm3(instance: Instance) -> int:
    cg1 = cg2 = cg3 = cg4 = 0
    for t in instance.t:
        if t * 3 > instance.c * 2:
            cg1 += 1
        elif t * 3 == instance.c * 2:
            cg2 += 1
        elif t * 3 > instance.c:
            cg3 += 1
        elif t * 3 == instance.c:
            cg4 += 1

    total = 6 * cg1 + 4 * cg2 + 3 * cg3 + 2 * cg4
    if total % 6 == 0:
        return total // 6
    return total // 6 + 1


@dataclass
class LowerBounds:
    lm1: int
    lms1: int
    lm2: int
    lm3: int

    @property
    def best(self) -> int:
        return max(self.lm1, self.lms1, self.lm2, self.lm3)


def compute_lower_bounds(instance: Instance) -> LowerBounds:
    return LowerBounds(
        lm1=lm1(instance),
        lms1=lms1(instance),
        lm2=lm2(instance),
        lm3=lm3(instance),
    )
