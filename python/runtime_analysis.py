from __future__ import annotations

import argparse
import csv
import time
from collections import defaultdict
from pathlib import Path

if __package__ in (None, ""):
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.append(str(repo_root))
    __package__ = "python"

from .heuristics import sample_solution
from .instance import Instance
from .preprocessing import preprocess


DATASETS_ROOT = Path(__file__).resolve().parent / "DataSets"
RESULTS_ROOT = Path(__file__).resolve().parents[1] / "results"


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def iter_normal_datasets() -> list[Path]:
    datasets: list[Path] = []
    for folder in ("DataSet_SBF1", "DataSet SBF2"):
        root = DATASETS_ROOT / folder
        if root.exists():
            datasets.extend(
                sorted(
                    path
                    for path in root.rglob("*.alb")
                    if not path.name.endswith("_extended.alb")
                )
            )
    return datasets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runtime analysis for base SUALBSP datasets.")
    parser.add_argument("--runtime", action="store_true", help="Run runtime aggregation.")
    parser.add_argument(
        "--runtime-cumulative",
        action="store_true",
        help="Create cumulative runtime tuples from an existing runtime_tuples.csv only.",
    )
    parser.add_argument("--seed", type=int, default=1, help="Random seed.")
    parser.add_argument("--iter", type=_positive_int, default=100, help="Number of sampling iterations.")
    parser.add_argument(
        "--measure",
        choices=("solve", "full"),
        default="solve",
        help="Measure only solve time or read+preprocess+solve.",
    )
    return parser.parse_args()


def results_dir(iterations: int) -> Path:
    return RESULTS_ROOT / f"results {iterations} iterations"


def write_runtime_files(
    iterations: int,
    raw_rows: list[tuple[str, int, float, str]],
    grouped_rows: list[tuple[int, float, int]],
) -> tuple[Path, Path]:
    out_dir = results_dir(iterations)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "runtime_raw.csv"
    tuples_path = out_dir / "runtime_tuples.csv"

    with raw_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("dataset", "task_count", "runtime_sec", "status"))
        writer.writerows(raw_rows)

    with tuples_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("task_count", "avg_runtime_sec", "num_instances"))
        writer.writerows(grouped_rows)

    return raw_path, tuples_path


def write_cumulative_runtime_file(iterations: int) -> Path:
    out_dir = results_dir(iterations)
    tuples_path = out_dir / "runtime_tuples.csv"
    cumulative_path = out_dir / "cumulative_runtime_tuples.csv"
    if not tuples_path.exists():
        raise SystemExit(f"Missing input file: {tuples_path}")

    rows: list[tuple[int, float, int]] = []
    with tuples_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                (
                    int(row["task_count"]),
                    float(row["avg_runtime_sec"]),
                    int(row["num_instances"]),
                )
            )

    rows.sort(key=lambda row: row[0])

    cumulative = 0.0
    with cumulative_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("task_count", "avg_runtime_sec", "cumulative_avg_runtime_sec", "num_instances"))
        for task_count, avg_runtime, num_instances in rows:
            cumulative += avg_runtime
            writer.writerow((task_count, avg_runtime, cumulative, num_instances))

    return cumulative_path


def select_datasets(paths: list[Path]) -> list[Path]:
    while True:
        answer = input("Gesamter Durchlauf? [y/n]: ").strip().lower()
        if answer == "y":
            return paths
        if answer == "n":
            return paths[:20]
        print("Bitte y oder n eingeben.")


def solve_instance(path: Path, args: argparse.Namespace) -> tuple[int, float, str]:
    task_count = -1
    start = time.perf_counter()
    preprocessed: float | None = None

    try:
        instance = Instance.read_sbf(path)
        task_count = instance.n
        preprocess(instance)
        preprocessed = time.perf_counter()
        result = sample_solution(instance, seed=args.seed, iterations=args.iter)
        end = time.perf_counter()
        runtime = end - start if args.measure == "full" else end - preprocessed
        status = "ok" if result.order and result.station_assignment else "keine_loesung"
        return task_count, runtime, status
    except Exception:
        end = time.perf_counter()
        if args.measure == "full" or preprocessed is None:
            runtime = end - start
        else:
            runtime = end - preprocessed
        return task_count, runtime, "keine_loesung"


def main() -> None:
    args = parse_args()

    if args.runtime_cumulative:
        cumulative_path = write_cumulative_runtime_file(args.iter)
        print(f"Wrote cumulative runtime tuples to {cumulative_path}")
        return

    if not args.runtime:
        raise SystemExit("Use --runtime to start runtime aggregation.")

    paths = select_datasets(iter_normal_datasets())
    runtime_by_tasks: dict[int, list[float]] = defaultdict(list)
    raw_rows: list[tuple[str, int, float, str]] = []

    for path in paths:
        task_count, runtime, status = solve_instance(path, args)
        raw_rows.append((str(path), task_count, runtime, status))
        if task_count >= 0:
            runtime_by_tasks[task_count].append(runtime)
        print(f"{path}: tasks={task_count} runtime={runtime:.6f}s status={status}")

    grouped_rows: list[tuple[int, float, int]] = []
    for task_count in sorted(runtime_by_tasks):
        values = runtime_by_tasks[task_count]
        grouped_rows.append((task_count, sum(values) / len(values), len(values)))

    raw_path, tuples_path = write_runtime_files(args.iter, raw_rows, grouped_rows)
    cumulative_path = write_cumulative_runtime_file(args.iter)
    print(f"Wrote raw runtimes to {raw_path}")
    print(f"Wrote runtime tuples to {tuples_path}")
    print(f"Wrote cumulative runtime tuples to {cumulative_path}")


if __name__ == "__main__":
    main()
