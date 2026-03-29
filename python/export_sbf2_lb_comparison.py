from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.instance import Instance
from python.lowerbounds import compute_lower_bounds
from python.preprocessing import preprocess

# ---------------------------
# Default paths
# ---------------------------
# Paths inferred from the repository tree
DEFAULT_SBF2_DIR = REPO_ROOT / "python" / "DataSets" / "DataSet SBF2"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results"

ALPHA_ORDER = (0.25, 0.50, 0.75, 1.00)
ALPHA_PATTERN = re.compile(r"(?:alpha|a)[_\- ]*(0?\.\d+|\d+(?:\.\d+)?)", re.IGNORECASE)
GENERIC_ALPHA_VALUE_PATTERN = re.compile(r"(?<!\d)(0?\.\d+|1(?:\.0+)?)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate SBF2 lower bounds vs. known optimum station counts."
    )
    parser.add_argument(
        "--sbf2-dir",
        type=Path,
        default=DEFAULT_SBF2_DIR,
        help=f"Path to SBF2 dataset directory (default: {DEFAULT_SBF2_DIR})",
    )
    parser.add_argument(
        "--per-instance-csv",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "sbf2_lb_per_instance.csv",
        help="Output CSV path for per-instance rows.",
    )
    parser.add_argument(
        "--summary-csv",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "sbf2_lb_summary_by_alpha.csv",
        help="Output CSV path for alpha-group summary rows.",
    )
    parser.add_argument(
        "--parse-errors-csv",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "sbf2_lb_parse_errors.csv",
        help="Output CSV path for files that the current parser cannot read.",
    )
    return parser.parse_args()


def normalize_alpha(value: float) -> float | None:
    for candidate in ALPHA_ORDER:
        if abs(value - candidate) < 1e-6:
            return candidate
    return None


def detect_alpha(path: Path) -> float | None:
    """
    Detect alpha from file and parent directory names
    Accepts patterns like alpha0.25, alpha_0.5, and a0.75
    """
    search_space = [path.name] + [part for part in path.parts]
    for token in search_space:
        match = ALPHA_PATTERN.search(token)
        if not match:
            continue
        try:
            parsed = float(match.group(1))
        except ValueError:
            continue
        normalized = normalize_alpha(parsed)
        if normalized is not None:
            return normalized

    # Fallback for tokens containing 25, 50, 75, or 100 with alpha hints
    lowered_parts = [p.lower() for p in path.parts]
    for part in lowered_parts:
        generic_match = GENERIC_ALPHA_VALUE_PATTERN.search(part)
        if generic_match:
            try:
                normalized = normalize_alpha(float(generic_match.group(1)))
            except ValueError:
                normalized = None
            if normalized is not None:
                return normalized

        if "alpha" in part:
            if "25" in part:
                return 0.25
            if "50" in part:
                return 0.50
            if "75" in part:
                return 0.75
            if "100" in part or "1.00" in part or "1_00" in part:
                return 1.00

    return None


def prompt_use_lm4() -> bool:
    """Ask whether LM4 should be included in the benchmark run"""
    while True:
        answer = input("Include LM4 in the benchmark? [y/n]: ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer with 'y' or 'n'.")


def compute_bounds(instance: Instance, use_lm4: bool) -> dict[str, int | None]:
    """Compute lower bounds from the current Python implementation"""
    bounds_obj = compute_lower_bounds(instance, use_lm4=use_lm4)

    values = {
        "lm1": getattr(bounds_obj, "lm1", None),
        "lms1": getattr(bounds_obj, "lms1", None),
        "lm2": getattr(bounds_obj, "lm2", None),
        "lm3": getattr(bounds_obj, "lm3", None),
        "lm4": getattr(bounds_obj, "lm4", None),
    }

    return values


def gap_pct(opt: int, lb: int | None) -> float | None:
    if lb is None:
        return None
    if opt <= 0:
        return None
    return (opt - lb) / opt * 100.0


def fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "-"
    return f"{value:.{digits}f}"


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def main() -> None:
    args = parse_args()
    sbf2_dir: Path = args.sbf2_dir
    use_lm4 = prompt_use_lm4()

    if not sbf2_dir.exists():
        raise FileNotFoundError(f"SBF2 directory not found: {sbf2_dir}")

    alb_files = sorted(p for p in sbf2_dir.rglob("*.alb") if p.is_file())
    if not alb_files:
        raise FileNotFoundError(f"No .alb files found in: {sbf2_dir}")

    per_instance_rows: list[dict[str, Any]] = []
    parse_error_rows: list[dict[str, str]] = []
    skipped_missing_alpha = 0
    skipped_missing_opt = 0

    for alb_path in alb_files:
        alpha = detect_alpha(alb_path)
        if alpha is None:
            skipped_missing_alpha += 1
            continue

        try:
            instance = Instance.read_sbf(alb_path)
        except Exception as exc:
            parse_error_rows.append(
                {
                    "alpha": f"{alpha:.2f}",
                    "instance": alb_path.name,
                    "path": str(alb_path),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
            continue

        opt = instance.optm
        if opt is None:
            # Skip instances without known optimum
            skipped_missing_opt += 1
            continue

        preprocess(instance)
        lbs = compute_bounds(instance, use_lm4=use_lm4)

        row = {
            "alpha": f"{alpha:.2f}",
            "instance": alb_path.name,
            "n": instance.n,
            "opt": opt,
            "lm1": lbs["lm1"],
            "lms1": lbs["lms1"],
            "lm2": lbs["lm2"],
            "lm3": lbs["lm3"],
            "lm4": lbs["lm4"],
            "gap_lm1_pct": gap_pct(opt, lbs["lm1"]),
            "gap_lms1_pct": gap_pct(opt, lbs["lms1"]),
            "gap_lm2_pct": gap_pct(opt, lbs["lm2"]),
            "gap_lm3_pct": gap_pct(opt, lbs["lm3"]),
            "gap_lm4_pct": gap_pct(opt, lbs["lm4"]),
        }
        per_instance_rows.append(row)

    # Group summary by alpha
    grouped: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for row in per_instance_rows:
        grouped[float(row["alpha"])].append(row)

    summary_rows: list[dict[str, Any]] = []
    for alpha in ALPHA_ORDER:
        rows = grouped.get(alpha, [])
        summary_rows.append(
            {
                "alpha": f"{alpha:.2f}",
                "N": len(rows),
                "avg_gap_lm1_pct": mean([r["gap_lm1_pct"] for r in rows if r["gap_lm1_pct"] is not None]),
                "avg_gap_lms1_pct": mean([r["gap_lms1_pct"] for r in rows if r["gap_lms1_pct"] is not None]),
                "avg_gap_lm2_pct": mean([r["gap_lm2_pct"] for r in rows if r["gap_lm2_pct"] is not None]),
                "avg_gap_lm3_pct": mean([r["gap_lm3_pct"] for r in rows if r["gap_lm3_pct"] is not None]),
                "avg_gap_lm4_pct": mean([r["gap_lm4_pct"] for r in rows if r["gap_lm4_pct"] is not None]),
            }
        )

    summary_rows.append(
        {
            "alpha": "avg",
            "N": len(ALPHA_ORDER),
            "avg_gap_lm1_pct": mean([row["avg_gap_lm1_pct"] for row in summary_rows if row["avg_gap_lm1_pct"] is not None]),
            "avg_gap_lms1_pct": mean([row["avg_gap_lms1_pct"] for row in summary_rows if row["avg_gap_lms1_pct"] is not None]),
            "avg_gap_lm2_pct": mean([row["avg_gap_lm2_pct"] for row in summary_rows if row["avg_gap_lm2_pct"] is not None]),
            "avg_gap_lm3_pct": mean([row["avg_gap_lm3_pct"] for row in summary_rows if row["avg_gap_lm3_pct"] is not None]),
            "avg_gap_lm4_pct": mean([row["avg_gap_lm4_pct"] for row in summary_rows if row["avg_gap_lm4_pct"] is not None]),
        }
    )

    args.per_instance_csv.parent.mkdir(parents=True, exist_ok=True)
    args.summary_csv.parent.mkdir(parents=True, exist_ok=True)
    args.parse_errors_csv.parent.mkdir(parents=True, exist_ok=True)

    per_instance_fields = [
        "alpha",
        "instance",
        "n",
        "opt",
        "lm1",
        "lms1",
        "lm2",
        "lm3",
        "lm4",
        "gap_lm1_pct",
        "gap_lms1_pct",
        "gap_lm2_pct",
        "gap_lm3_pct",
        "gap_lm4_pct",
    ]
    with args.per_instance_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=per_instance_fields)
        writer.writeheader()
        writer.writerows(per_instance_rows)

    summary_fields = [
        "alpha",
        "N",
        "avg_gap_lm1_pct",
        "avg_gap_lms1_pct",
        "avg_gap_lm2_pct",
        "avg_gap_lm3_pct",
        "avg_gap_lm4_pct",
    ]
    with args.summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    parse_error_fields = ["alpha", "instance", "path", "error_type", "error_message"]
    with args.parse_errors_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=parse_error_fields)
        writer.writeheader()
        writer.writerows(parse_error_rows)

    # Console summary table
    print("SBF2 Lower-Bound Gap Summary by alpha")
    print("(gap = (opt - lb) / opt * 100)")
    print("-" * 90)
    print(
        f"{'alpha':>7} {'N':>6} {'LM1':>10} {'LMS1':>10} {'LM2':>10} {'LM3':>10} {'LM4':>10}"
    )
    for row in summary_rows:
        print(
            f"{row['alpha']:>7} "
            f"{str(row['N']):>6} "
            f"{fmt_num(row['avg_gap_lm1_pct']):>10} "
            f"{fmt_num(row['avg_gap_lms1_pct']):>10} "
            f"{fmt_num(row['avg_gap_lm2_pct']):>10} "
            f"{fmt_num(row['avg_gap_lm3_pct']):>10} "
            f"{fmt_num(row['avg_gap_lm4_pct']):>10}"
        )

    print("-" * 90)
    print(f"Per-instance CSV: {args.per_instance_csv}")
    print(f"Summary CSV:      {args.summary_csv}")
    print(f"Parse errors CSV: {args.parse_errors_csv}")
    print(f"Found .alb files: {len(alb_files)}")
    print(f"Skipped (alpha not detected): {skipped_missing_alpha}")
    print(f"Skipped (missing opt):        {skipped_missing_opt}")
    print(f"Skipped (parser errors):      {len(parse_error_rows)}")
    print(f"Processed instances with known opt: {len(per_instance_rows)}")
    if parse_error_rows:
        print("First parser-error files:")
        for row in parse_error_rows[:5]:
            print(f"  - {row['path']} [{row['error_type']}: {row['error_message']}]")


if __name__ == "__main__":
    main()
