from __future__ import annotations

from .instance import Instance


def transitive_closure(matrix: list[list[bool]]) -> list[list[bool]]:
    n = len(matrix)
    closure = [row[:] for row in matrix]
    for k in range(n):
        for i in range(n):
            if closure[i][k]:
                row = closure[i]
                krow = closure[k]
                for j in range(n):
                    row[j] = row[j] or krow[j]
    return closure


def compute_precedence_sets(instance: Instance) -> None:
    n = instance.n
    instance.P = [[] for _ in range(n)]
    instance.F = [[] for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if instance.d[i][j]:
                instance.F[i].append(j)
                instance.P[j].append(i)

    instance.D = transitive_closure(instance.d)

    instance.Ps = [[] for _ in range(n)]
    instance.Fs = [[] for _ in range(n)]
    instance.Is = [[] for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if instance.D[i][j]:
                instance.Fs[i].append(j)
                instance.Ps[j].append(i)
            elif not instance.D[j][i] and i < j:
                instance.Is[i].append(j)
                instance.Is[j].append(i)


def compute_smallest_setups(instance: Instance) -> None:
    n = instance.n
    c = instance.c

    sfi = []
    sbi = []
    for i in range(n):
        if n == 1:
            min_sf = c
        else:
            min_sf = min(instance.sf[i][j] for j in range(n) if i != j)
        min_sb = min(instance.sb[i][j] for j in range(n))
        sfi.append(min_sf if min_sf <= c else c)
        sbi.append(min_sb if min_sb <= c else c)

    instance.sfi = sorted(sfi)
    instance.sbi = sorted(sbi)


def compute_ta_tn(instance: Instance) -> None:
    n = instance.n
    instance.ta = [0] * n
    instance.tn = [0] * n
    for i in range(n):
        for j in range(n):
            if instance.D[j][i]:
                instance.ta[i] += instance.t[j]
            if instance.D[i][j]:
                instance.tn[i] += instance.t[j]


def compute_E_T(instance: Instance) -> None:
    n = instance.n
    c = instance.c
    instance.E = [0] * n
    instance.T = [0] * n
    for i in range(n):
        instance.E[i] = (instance.ta[i] + instance.t[i] + c - 1) // c
    for i in range(n):
        instance.T[i] = (instance.t[i] + instance.tn[i] + c - 1) // c


def preprocess(instance: Instance) -> None:
    compute_precedence_sets(instance)
    compute_smallest_setups(instance)
    compute_ta_tn(instance)
    compute_E_T(instance)
