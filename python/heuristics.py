from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .instance import Instance


def topological_random_order(instance: Instance, rng: Random) -> list[int]:
    indeg = [len(instance.P[i]) for i in range(instance.n)]
    available = [i for i in range(instance.n) if indeg[i] == 0]
    order = []

    while available:
        idx = rng.randrange(len(available))
        available[idx], available[-1] = available[-1], available[idx]
        task = available.pop()
        order.append(task)
        for succ in instance.F[task]:
            indeg[succ] -= 1
            if indeg[succ] == 0:
                available.append(succ)
    return order


def next_station(instance: Instance, order: list[int], start: int) -> int:
    idx = start
    load = instance.t[order[start]]
    j = start + 1
    while j < instance.n:
        load += instance.sf[order[j - 1]][order[j]] + instance.t[order[j]]
        if load + instance.sb[order[j]][order[start]] <= instance.c:
            idx = j
        j += 1
    return idx + 1


def assign_stations(instance: Instance, order: list[int]) -> tuple[list[int], int]:
    assignment = [0] * instance.n
    station = 1
    idx = 0
    while idx < instance.n:
        next_idx = next_station(instance, order, idx)
        for pos in range(idx, next_idx):
            assignment[pos] = station
        station += 1
        idx = next_idx
    return assignment, station - 1


@dataclass
class HeuristicResult:
    order: list[int]
    station_assignment: list[int]
    stations: int


def sample_solution(instance: Instance, seed: int, iterations: int) -> HeuristicResult:
    rng = Random(seed)
    best_order: list[int] = []
    best_assignment: list[int] = []
    best_stations = instance.n

    for _ in range(iterations):
        order = topological_random_order(instance, rng)
        assignment, stations = assign_stations(instance, order)
        if stations < best_stations:
            best_stations = stations
            best_order = order
            best_assignment = assignment

    return HeuristicResult(best_order, best_assignment, best_stations)
