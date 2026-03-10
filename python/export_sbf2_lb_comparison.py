from __future__ import annotations

"""
Evaluate SBF2 lower-bound quality against known optimal station counts.

This script reuses the repository's existing Python implementation:
- Instance.read_sbf(...)
- preprocess(instance)
- compute_lower_bounds(...)

It scans SBF2 .alb files, computes LM1/LMS1/LM2/LM3/(LM4 if available),
computes per-instance percentage gaps to known optima, and exports:
1) a per-instance CSV
2) a summary CSV grouped by alpha in {0.25, 0.50, 0.75, 1.00}
3) a compact console table
"""

import argparse
import csv
import inspect
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
# Configurable default paths
# ---------------------------
# Paths inferred from the repository tree shown by the user.
DEFAULT_SBF2_DIR = REPO_ROOT / "python" / "DataSets" / "DataSet SBF2"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results"

ALPHA_ORDER = (0.25, 0.50, 0.75, 1.00)
ALPHA_PATTERN = re.compile(r"(?:alpha|a)[_\- ]*(0?\.\d+|\d+(?:\.\d+)?)", re.IGNORECASE)


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
    return parser.parse_args()


def normalize_alpha(value: float) -> float | None:
    for candidate in ALPHA_ORDER:
        if abs(value - candidate) < 1e-6:
            return candidate
    return None


def detect_alpha(path: Path) -> float | None:
    """
    Detect alpha from file name and/or parent directory names.
    Accepts patterns like alpha0.25, alpha_0.5, a0.75, etc.
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

    # Fallback for plain folder/file tokens containing 25/50/75/100 with alpha hints.
    lowered_parts = [p.lower() for p in path.parts]
    for part in lowered_parts:
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


def compute_bounds(instance: Instance) -> dict[str, int | None]:
    """
    Call compute_lower_bounds while remaining compatible with signatures
    with/without a use_lm4 argument.
    """
    signature = inspect.signature(compute_lower_bounds)
    if "use_lm4" in signature.parameters:
        bounds_obj = compute_lower_bounds(instance, use_lm4=True)
    else:
        bounds_obj = compute_lower_bounds(instance)

    values = {
        "lm1": getattr(bounds_obj, "lm1", None),
        "lms1": getattr(bounds_obj, "lms1", None),
        "lm2": getattr(bounds_obj, "lm2", None),
        "lm3": getattr(bounds_obj, "lm3", None),
        "lm4": getattr(bounds_obj, "lm4", None),
    }

    # Optional fallback: some versions expose lm4 as a module-level function.
    if values["lm4"] is None:
        try:
            from python import lowerbounds as lb_module

            lm4_func = getattr(lb_module, "lm4", None)
            if callable(lm4_func):
                values["lm4"] = int(lm4_func(instance))
        except Exception:
            # Keep evaluation-only script robust; missing LM4 is allowed.
            pass

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

    if not sbf2_dir.exists():
        raise FileNotFoundError(f"SBF2 directory not found: {sbf2_dir}")

    alb_files = sorted(p for p in sbf2_dir.rglob("*.alb") if p.is_file())
    if not alb_files:
        raise FileNotFoundError(f"No .alb files found in: {sbf2_dir}")

    per_instance_rows: list[dict[str, Any]] = []

    for alb_path in alb_files:
        alpha = detect_alpha(alb_path)
        if alpha is None:
            continue

        instance = Instance.read_sbf(alb_path)
        opt = instance.optm
        if opt is None:
            # Required by task: skip instances without known optimum.
            continue

        preprocess(instance)
        lbs = compute_bounds(instance)

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

    # Group summary by alpha.
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

    args.per_instance_csv.parent.mkdir(parents=True, exist_ok=True)
    args.summary_csv.parent.mkdir(parents=True, exist_ok=True)

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

    # Console summary table.
    print("SBF2 Lower-Bound Gap Summary by alpha")
    print("(gap = (opt - lb) / opt * 100)")
    print("-" * 90)
    print(
        f"{'alpha':>7} {'N':>6} {'LM1':>10} {'LMS1':>10} {'LM2':>10} {'LM3':>10} {'LM4':>10}"
    )
    for row in summary_rows:
        print(
            f"{row['alpha']:>7} "
            f"{row['N']:>6d} "
            f"{fmt_num(row['avg_gap_lm1_pct']):>10} "
            f"{fmt_num(row['avg_gap_lms1_pct']):>10} "
            f"{fmt_num(row['avg_gap_lm2_pct']):>10} "
            f"{fmt_num(row['avg_gap_lm3_pct']):>10} "
            f"{fmt_num(row['avg_gap_lm4_pct']):>10}"
        )

    print("-" * 90)
    print(f"Per-instance CSV: {args.per_instance_csv}")
    print(f"Summary CSV:      {args.summary_csv}")
    print(f"Processed instances with known opt: {len(per_instance_rows)}")


if __name__ == "__main__":
    main()
