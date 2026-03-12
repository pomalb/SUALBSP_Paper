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


def _round_up(value: int, capacity: int) -> int:
    return ceil_div(value, capacity) * capacity


def _can_forward_ext(instance: Instance, i: int, j: int) -> bool:
    return not (
        ((instance.D[i][j] and not instance.d[i][j]) or instance.D[j][i] or i == j)
        or instance.sf[i][j] > instance.c
    )


def _can_backward_ext(instance: Instance, i: int, j: int) -> bool:
    return not (instance.D[i][j] or instance.sb[i][j] > instance.c)


def _is_triangular(instance: Instance) -> bool:
    cached = getattr(instance, "_lm4_is_triangular", None)
    if cached is not None:
        return cached

    n = instance.n
    triangular = True
    for i in range(n):
        bii = instance.sb[i][i]
        for j in range(n):
            if i == j:
                continue

            if _can_forward_ext(instance, i, j) and _can_backward_ext(instance, j, i):
                insertion = instance.sf[i][j] + instance.t[j] + instance.sb[j][i] - bii
                if insertion < 0:
                    triangular = False
                    break

            if _can_forward_ext(instance, j, i) and _can_backward_ext(instance, i, j):
                insertion = instance.sf[j][i] + instance.t[j] + instance.sb[i][j] - bii
                if insertion < 0:
                    triangular = False
                    break

            for h in range(n):
                if h == i or h == j:
                    continue
                if (
                    _can_forward_ext(instance, i, h)
                    and _can_forward_ext(instance, h, j)
                    and _can_forward_ext(instance, i, j)
                ):
                    insertion = instance.sf[i][h] + instance.t[h] + instance.sf[h][j] - instance.sf[i][j]
                    if insertion < 0:
                        triangular = False
                        break
                if (
                    _can_forward_ext(instance, i, h)
                    and _can_backward_ext(instance, h, j)
                    and _can_backward_ext(instance, i, j)
                ):
                    insertion = instance.sf[i][h] + instance.t[h] + instance.sb[h][j] - instance.sb[i][j]
                    if insertion < 0:
                        triangular = False
                        break
            if not triangular:
                break
        if not triangular:
            break

    setattr(instance, "_lm4_is_triangular", triangular)
    return triangular


def _lm4_min_setups(instance: Instance, task: int, use_successors: bool, triangular: bool) -> tuple[int, int]:
    c = instance.c
    min_fs = c
    min_bs = c

    if use_successors:
        if triangular:
            for other in instance.F[task]:
                min_fs = min(min_fs, instance.sf[task][other])
            for other in instance.Fs[task]:
                min_bs = min(min_bs, instance.sb[other][task])
        else:
            for other in instance.Fs[task]:
                min_fs = min(min_fs, instance.sf[task][other])
                min_bs = min(min_bs, instance.sb[other][task])
            for other in instance.Is[task]:
                min_fs = min(min_fs, instance.sf[task][other])
                min_bs = min(min_bs, instance.sb[other][task])
    else:
        if triangular:
            for other in instance.P[task]:
                min_fs = min(min_fs, instance.sf[other][task])
            for other in instance.Ps[task]:
                min_bs = min(min_bs, instance.sb[task][other])
        else:
            for other in instance.P[task]:
                min_fs = min(min_fs, instance.sf[other][task])
            for other in instance.Is[task]:
                min_fs = min(min_fs, instance.sf[other][task])
            for other in instance.Ps[task]:
                min_bs = min(min_bs, instance.sb[task][other])
            for other in instance.Is[task]:
                min_bs = min(min_bs, instance.sb[task][other])

    return min_fs, min_bs


def _lm4_side(instance: Instance, use_successors: bool, triangular: bool) -> int:
    n = instance.n
    related_sets = instance.Fs if use_successors else instance.Ps
    ordered_tasks = range(n - 1, -1, -1) if use_successors else range(n)

    partials = []
    for task in range(n):
        related_time = sum(instance.t[other] for other in related_sets[task])
        partials.append({"id": task, "t": related_time})
    partials.sort(key=lambda item: item["t"], reverse=True)

    for task in ordered_tasks:
        related = set(related_sets[task])
        acc = 0
        max_acc = 0
        for item in partials:
            if item["id"] in related:
                acc += instance.t[item["id"]]
                max_acc = max(max_acc, acc + item["t"])

        if max_acc > 0:
            if instance.t[task] == instance.c or max_acc % instance.c == 0:
                max_acc = _round_up(max_acc, instance.c)
            else:
                min_fs, min_bs = _lm4_min_setups(instance, task, use_successors, triangular)
                next_multiple = _round_up(max_acc, instance.c)
                if min_fs + min_bs >= instance.c:
                    max_acc = next_multiple
                elif max_acc + instance.t[task] + min_fs + min_bs > next_multiple:
                    max_acc = next_multiple
                else:
                    max_acc += min_fs

        for item in partials:
            if item["id"] == task:
                item["t"] = max_acc
                break
        partials.sort(key=lambda item: item["t"], reverse=True)

    acc = 0
    max_acc = 0
    for item in partials:
        acc += instance.t[item["id"]]
        max_acc = max(max_acc, acc + item["t"])
    return ceil_div(max_acc, instance.c)


def lm4(instance: Instance) -> int:
    triangular = _is_triangular(instance)
    return max(
        _lm4_side(instance, use_successors=True, triangular=triangular),
        _lm4_side(instance, use_successors=False, triangular=triangular),
    )


@dataclass
class LowerBounds:
    lm1: int
    lms1: int
    lm2: int
    lm3: int
    lm4: int | None = None

    @property
    def best(self) -> int:
        values = [self.lm1, self.lms1, self.lm2, self.lm3]
        if self.lm4 is not None:
            values.append(self.lm4)
        return max(values)


def compute_lower_bounds(instance: Instance, use_lm4: bool = True) -> LowerBounds:
    return LowerBounds(
        lm1=lm1(instance),
        lms1=lms1(instance),
        lm2=lm2(instance),
        lm3=lm3(instance),
        lm4=lm4(instance) if use_lm4 else None,
    )
