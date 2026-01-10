from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


def _blank_line(line: str) -> bool:
    return line.strip() == ""


def _normalize_section(line: str) -> str:
    line = line.strip()
    if line.startswith("<") and line.endswith(">"):
        return line[1:-1].strip().lower()
    return ""


@dataclass
class Instance:
    n: int = 0
    c: int = 0
    optm: int | None = None

    t0: list[int] = field(default_factory=list)
    t: list[int] = field(default_factory=list)

    d: list[list[bool]] = field(default_factory=list)
    sf: list[list[int]] = field(default_factory=list)
    sb: list[list[int]] = field(default_factory=list)

    P: list[list[int]] = field(default_factory=list)
    F: list[list[int]] = field(default_factory=list)
    Ps: list[list[int]] = field(default_factory=list)
    Fs: list[list[int]] = field(default_factory=list)
    Is: list[list[int]] = field(default_factory=list)

    D: list[list[bool]] = field(default_factory=list)

    sfi: list[int] = field(default_factory=list)
    sbi: list[int] = field(default_factory=list)

    ta: list[int] = field(default_factory=list)
    tn: list[int] = field(default_factory=list)
    E: list[int] = field(default_factory=list)
    T: list[int] = field(default_factory=list)

    setup_directed: bool = True

    def allocate(self, n: int) -> None:
        self.n = n
        self.t0 = [0] * n
        self.t = [0] * n
        self.d = [[False] * n for _ in range(n)]
        self.sf = [[0] * n for _ in range(n)]
        self.sb = [[0] * n for _ in range(n)]

    @classmethod
    def read_sbf(cls, path: str | Path) -> "Instance":
        instance = cls()
        path = Path(path)
        with path.open("r", encoding="utf-8") as handle:
            lines = [line.rstrip("\n") for line in handle]

        idx = 0
        seen_forward = False
        seen_backward = False
        while idx < len(lines):
            section = _normalize_section(lines[idx])
            if not section:
                idx += 1
                continue
            idx += 1

            if section == "number of tasks":
                while idx < len(lines) and _blank_line(lines[idx]):
                    idx += 1
                instance.allocate(int(lines[idx].strip()))
                idx += 1
            elif section == "cycle time":
                while idx < len(lines) and _blank_line(lines[idx]):
                    idx += 1
                instance.c = int(lines[idx].strip())
                idx += 1
            elif section == "task times":
                while idx < len(lines) and _blank_line(lines[idx]):
                    idx += 1
                while idx < len(lines) and not _blank_line(lines[idx]):
                    parts = lines[idx].split()
                    task_id = int(parts[0]) - 1
                    instance.t0[task_id] = int(parts[1])
                    idx += 1
            elif section == "precedence relations":
                while idx < len(lines) and _blank_line(lines[idx]):
                    idx += 1
                while idx < len(lines) and not _blank_line(lines[idx]):
                    pred, succ = lines[idx].split(",")
                    instance.d[int(pred) - 1][int(succ) - 1] = True
                    idx += 1
            elif section == "setup times forward":
                seen_forward = True
                while idx < len(lines) and _blank_line(lines[idx]):
                    idx += 1
                while idx < len(lines) and not _blank_line(lines[idx]):
                    pair, value = lines[idx].split(":")
                    pred, succ = pair.split(",")
                    instance.sf[int(pred) - 1][int(succ) - 1] = int(value)
                    idx += 1
            elif section == "setup times backward":
                seen_backward = True
                while idx < len(lines) and _blank_line(lines[idx]):
                    idx += 1
                while idx < len(lines) and not _blank_line(lines[idx]):
                    pair, value = lines[idx].split(":")
                    pred, succ = pair.split(",")
                    instance.sb[int(pred) - 1][int(succ) - 1] = int(value)
                    idx += 1
            elif section == "optimal salbp-1 value":
                while idx < len(lines) and _blank_line(lines[idx]):
                    idx += 1
                instance.optm = int(lines[idx].strip())
                idx += 1
            elif section == "end":
                idx += 1
                continue
            else:
                idx += 1

        instance.setup_directed = seen_forward or seen_backward
        instance.t = list(instance.t0)
        return instance

    def clone_matrix(self, matrix: list[list[int]]) -> list[list[int]]:
        return [row[:] for row in matrix]

    def iter_tasks(self) -> Iterable[int]:
        return range(self.n)
