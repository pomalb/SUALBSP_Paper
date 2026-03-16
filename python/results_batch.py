from __future__ import annotations

import argparse
from pathlib import Path

if __package__ in (None, ""):
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.append(str(repo_root))
    __package__ = "python"

from .heuristics import sample_solution
from .instance import Instance
from .lowerbounds import LowerBounds, compute_lower_bounds
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


def results_dir(iterations: int) -> Path:
    return RESULTS_ROOT / f"results {iterations} iterations"


def results_path(source_path: Path, iterations: int) -> Path:
    return results_dir(iterations) / source_path.relative_to(DATASETS_ROOT)


def format_bounds(bounds: LowerBounds | None) -> list[str]:
    if bounds is None:
        return ["keine Lower Bounds"]

    lines = [
        f"Lm1={bounds.lm1}",
        f"Lms1={bounds.lms1}",
        f"Lm2={bounds.lm2}",
        f"Lm3={bounds.lm3}",
    ]
    if bounds.lm4 is not None:
        lines.append(f"Lm4={bounds.lm4}")
    lines.append(f"Best={bounds.best}")
    return lines


def _clean_previous_result_blocks(lines: list[str]) -> list[str]:
    marker_prefixes = ("<Lower Bounds>", "<Optimal Stations (Iterations:")
    cleaned: list[str] = []
    skip_block = False

    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in marker_prefixes):
            skip_block = True
            continue
        if skip_block:
            if stripped == "":
                skip_block = False
            continue
        cleaned.append(line)

    while cleaned and cleaned[-1].strip() == "":
        cleaned.pop()
    return cleaned


def write_results_copy(
    source_path: Path,
    target_path: Path,
    bounds: LowerBounds | None,
    stations: int | None,
    iterations: int,
) -> None:
    source_lines = source_path.read_text(encoding="utf-8").splitlines()
    cleaned = _clean_previous_result_blocks(source_lines)
    cleaned.extend(("", "<Lower Bounds>", *format_bounds(bounds), ""))
    if stations is not None:
        cleaned.extend(
            (
                f"<Optimal Stations (Iterations: {iterations})>",
                str(stations),
                "",
            )
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("\n".join(cleaned), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch result export for base SUALBSP datasets.")
    parser.add_argument("--seed", type=int, default=1, help="Random seed.")
    parser.add_argument("--iter", type=_positive_int, default=100, help="Number of sampling iterations.")
    parser.add_argument("--no-lm4", action="store_true", help="Disable LM4.")
    parser.add_argument("--onlylb", action="store_true", help="Write only lower bounds, no station result.")
    parser.add_argument("--limit", type=_positive_int, default=None, help="Process only the first N datasets.")
    return parser.parse_args()


def process_instance(path: Path, args: argparse.Namespace) -> tuple[LowerBounds | None, int | None]:
    instance = Instance.read_sbf(path)
    preprocess(instance)
    bounds = compute_lower_bounds(instance, use_lm4=not args.no_lm4)
    if args.onlylb:
        return bounds, None
    result = sample_solution(instance, seed=args.seed, iterations=args.iter)
    stations = result.stations if result.order and result.station_assignment else None
    return bounds, stations


def main() -> None:
    args = parse_args()
    paths = iter_normal_datasets()
    if args.limit is not None:
        paths = paths[: args.limit]

    written = 0
    for path in paths:
        target = results_path(path, args.iter)
        try:
            bounds, stations = process_instance(path, args)
        except Exception:
            bounds, stations = None, None
        write_results_copy(path, target, bounds, stations, args.iter)
        print(f"{target}")
        written += 1

    print(f"Updated {written} result datasets in {results_dir(args.iter)}.")


if __name__ == "__main__":
    main()
