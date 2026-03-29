# SUALBSP

This repository contains the C++ implementation and supplementary experiment material for [New solution approaches for balancing assembly lines with setup times](https://doi.org/10.1016/j.cor.2025.107202).

The repository includes:
- the main C++ solver in `src/`,
- Python prototypes and analysis helpers in `python/`,
- generated experiment outputs and table scripts in `results/`.

## Quick Start

Build the C++ solver (`hs`):

```bash
cmake -S src -B build -G Ninja
cmake --build build
```

Show all command line options:

```bash
./build/hs --help
```

Run the solver on one instance with the sampling heuristic:

```bash
./build/hs --algorithm sampler --iterlimit 100 path/to/instance.alb
```

Run only lower bounds for one instance:

```bash
./build/hs --onlylb path/to/instance.alb
```

Run the paper-style low CBFS configuration:

```bash
./build/hs --iterlimit 100 --riterlimit 100 --dwlb -p ap --mprule --heavy-preprocess --algorithm S_hoffmann --cbfs --uselm4 --maxtimemodel 12 --exacttimelimit 120 --maxnodescbfs 1500 --secondpass path/to/instance.alb
```

Run the paper-style high CBFS configuration:

```bash
./build/hs --iterlimit 100 --riterlimit 100 --dwlb -p ap --mprule --heavy-preprocess --algorithm S_hoffmann --cbfs --uselm4 --maxtimemodel 24 --exacttimelimit 240 --maxnodescbfs 4500 --secondpass path/to/instance.alb
```

## C++ Solver Usage

The executable is `build/hs`. It reads one ALB instance, computes lower bounds first, then optionally runs a heuristic upper-bound procedure and finally CBFS if requested.

Typical run with a rule-based heuristic:

```bash
./build/hs --rule maxtminsu --iterlimit 200 --timelimit 600 path/to/instance.alb
```

Because `--rule` is set, the solver automatically switches from `sampler` to `rule`.

Run Hoffmann with a custom load cap:

```bash
./build/hs --algorithm hoffmann --maxloads 2000 path/to/instance.alb
```

Run forward and reverse search with the optimized rule variant:

```bash
./build/hs --algorithm ruleopt --rule asq --iterlimit 100 --riterlimit 100 path/to/instance.alb
```

Evaluate additional model-based lower bounds:

```bash
./build/hs --onlylb --dwlb --ssbf --maxtasks 100 --maxtimemodel 3600 path/to/instance.alb
```

Write the preprocessed instance to disk:

```bash
./build/hs --oinstance preprocessed.alb path/to/instance.alb
```

Export the relaxed SSBF model:

```bash
./build/hs --onlylb --ssbf --wrelaxation ssbf_relaxation.lp path/to/instance.alb
```

## Python Utilities

The `python/` folder contains a lightweight prototype solver and scripts for batch evaluation.

Run the Python prototype on one instance:

```bash
python3 -m python.main python/DataSets/MiniSet.alb --iter 100
```

Compute only lower bounds with the Python prototype:

```bash
python3 -m python.main python/DataSets/MiniSet.alb --onlylb
```

Export result copies for all datasets into `results/results X iterations/`:

```bash
python3 -m python.results_batch --iter 100
```

Write only lower bounds to the exported result copies:

```bash
python3 -m python.results_batch --iter 100 --onlylb
```

Run runtime benchmarking and write `runtime_raw.csv`, `runtime_tuples.csv`, and `cumulative_runtime_tuples.csv`:

```bash
python3 -m python.runtime_analysis --runtime --iter 100
```

The script then asks `Gesamter Durchlauf? [y/n]:`.
- `y` processes all discovered datasets.
- `n` processes only the first 20 datasets.

Create cumulative runtime tuples from an existing `runtime_tuples.csv` without re-running the solver:

```bash
python3 -m python.runtime_analysis --runtime-cumulative --iter 100
```

## High-Level Execution Flow

For the C++ solver, the typical flow is:
- parse the ALB instance,
- compute simple lower bounds (`lm1`, `lms1`, `lm2`, `lm3`, `lm4`),
- optionally evaluate DW and SSBF lower bounds,
- run the selected heuristic (`sampler`, `rule`, `ruleopt`, or a Hoffmann variant),
- optionally run CBFS as the exact improvement phase,
- print `LOWERBOUNDS` and `SUMMARY` lines to stdout.

For the Python prototype, the typical flow is:
- load the instance with `Instance.read_sbf(...)`,
- preprocess it,
- compute lower bounds,
- sample a heuristic solution,
- print a compact summary.

## Important CLI Options

- `--algorithm`: `sampler`, `rule`, `ruleopt`, `hoffmann`, `SW_hoffmann`, `FH_hoffmann`, `S_hoffmann`, `none`.
- `--rule` or `-R`: rule name for rule-based assignment.
- `--iterlimit` or `-i`: maximum number of forward iterations.
- `--riterlimit` or `-r`: maximum number of reverse-instance iterations.
- `--timelimit` or `-t`: heuristic time limit in seconds.
- `--seed`: random seed, where `0` means randomized seed selection.
- `--onlylb`: compute and print only lower bounds.
- `--heavy-preprocess`: enable stronger preprocessing.
- `--dwlb`: evaluate the Dantzig-Wolfe lower bound.
- `--pricing` or `-p`: DW pricing type, either `salbp` or `ap`.
- `--ssbf`: evaluate the SSBF lower bound.
- `--maxtimemodel`: time limit for DW and SSBF model solving.
- `--cbfs`: enable the exact CBFS phase.
- `--secondpass`: rerun CBFS with relaxed node limit if time remains.
- `--maxnodescbfs`: node-extension budget for CBFS.
- `--exacttimelimit`: time limit for the exact method.
- `--uselm4`: use `lm4` inside CBFS.
- `--oinstance`: write the preprocessed instance to a file.
- `--wrelaxation`: export the SSBF relaxation model.
- `--format`: input format `mp`, `sbf`, or `guess`.

## Rule Names

- `maxtminsu`
- `maxtminsuslack`
- `maxf`
- `minslack`
- `random`
- `mprule`
- `sbf`
- `randomfs`
- `asq`
- `anti-asq`
- `rule-grasp(r1,r2,...)`

## Input Format Notes

Instances are expected in ALB format, such as the SUALBSP benchmark instances from the [assembly-line-balancing.de](https://assembly-line-balancing.de/sualbsp/data-set-of-scholl-et-al-2013) data set.

The solver supports:
- `sbf`: Scholl, Boysen, Fliedner style instances,
- `mp`: Martino and Pastor style instances,
- `guess`: automatic selection from file extension and content conventions.

## Output Notes

The C++ solver writes its main results to stdout:
- `LOWERBOUNDS ...` contains the computed lower-bound values and, if enabled, DW/SSBF timings.
- `SUMMARY ...` contains the final algorithm tag, instance name, seed, best lower bound, best station count, and runtime counters.

Additional outputs:
- `--oinstance` writes a preprocessed ALB instance.
- `--wrelaxation` writes a model export for the SSBF relaxation.
- `--output` exists as a CLI option, but is currently not used by the checked-in implementation.

The Python batch scripts write result copies and CSV summaries below `results/results X iterations/`.

## Repository Overview

- `src/`: main C++ solver, lower bounds, heuristics, DW/SSBF models, and CBFS.
- `python/`: Python prototype solver and experiment helpers.
- `results/`: generated CSV summaries and the `tables.R` script for paper tables.
- `CITATION.bib`: BibTeX entry for the paper.

## Reproducing Tables

To reproduce the paper tables from the generated CSV files, run:

```bash
Rscript results/tables.R
```

## Requirements

The C++ build expects:
- a C++20 compiler,
- [CMake](https://cmake.org/),
- [Ninja](https://ninja-build.org/) when using the generator above,
- `fmt`,
- Boost with `program_options`, `timer`, `system`, `chrono`, and `filesystem`,
- IBM CPLEX for the DW/SSBF components.

## How to cite

```bibtex
@Article{Pereira.Ritt/2025,
  author =   {Jordi Pereira and Marcus Ritt},
  title =    {New solution approaches for balancing assembly lines with setup times},
  journal =  {Computers and Operations Research},
  volume =   {183},
  number =   {107202},
  month =    nov,
  doi =      {10.1016/j.cor.2025.107202},
  url =      {https://doi.org/10.1016/j.cor.2025.107202}
}
```
