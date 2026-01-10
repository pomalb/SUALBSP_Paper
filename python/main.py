from __future__ import annotations

import argparse
from pathlib import Path

from .heuristics import sample_solution
from .instance import Instance
from .lowerbounds import compute_lower_bounds
from .preprocessing import preprocess


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SUALBSP solver (Python prototype).")
    parser.add_argument("instance", type=Path, help="Path to .alb instance file.")
    parser.add_argument("--seed", type=int, default=1, help="Random seed.")
    parser.add_argument("--iter", type=int, default=100, help="Number of sampling iterations.")
    parser.add_argument("--onlylb", action="store_true", help="Compute only lower bounds.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    instance = Instance.read_sbf(args.instance)
    preprocess(instance)

    bounds = compute_lower_bounds(instance)
    print(
        "LOWERBOUNDS",
        args.instance.stem,
        instance.n,
        bounds.lm1,
        bounds.lms1,
        bounds.lm2,
        bounds.lm3,
        bounds.best,
    )

    if args.onlylb:
        return

    result = sample_solution(instance, seed=args.seed, iterations=args.iter)
    print("SUMMARY", args.instance.stem, "stations", result.stations)


if __name__ == "__main__":
    main()
