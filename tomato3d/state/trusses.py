"""Trusses and segments (MTG Amendment A5): human truss registry, truss vertices, ``segment_index``.

User decisions of 2026-10-12 (``user_stated``):

* side shoots bear trusses (user observation); the determinate program is judged per axis, substems included;
* a sympodial continuation above a truss is ONE axis: the axis id stays ``M`` (or ``S1``), leaf ranks run on
  unbroken, the axis is never split. The truss is recorded at its node and every node carries
  ``segment_index`` - 1-based, incremented at each truss on that axis - so "leaves between trusses" is countable.

Trusses have no detector and no synthetic geometry (``tomato3d/synth/`` contains none, checked 2026-10-12), so
they are human-recorded like side shoots: ``data/records/trusses/truss_registry.csv`` (human-owned, read-only;
template under ``build/``). ``segment_index`` is DERIVED from that registry plus the leaf ranks - never
hand-entered, never guessed from a photo:

* a truss with ``above_rank = a`` sits on its axis directly above the leaf of rank a; the leaf of rank r is in
  segment ``1 + (trusses on the same axis with a < r)``; a truss is in the segment it closes;
* a snapshot uses only trusses recorded on or before its capture (no look-ahead); a truss recorded later can
  therefore raise the index of a leaf already ranked in an earlier snapshot (logged in ``change_log.csv``);
* no registry -> every ``segment_index`` is ``unavailable`` (absence of a record is not "no truss");
  a truss without ``above_rank`` -> the leaves of that axis stay ``unavailable``; the axis's apical segment
  (1 + its trusses) is still known.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import schema as s
from tomato3d.state.axes import CaptureClock, RegistryEntry

REGISTRY_PATH = Path("data/records/trusses/truss_registry.csv")
#: Columns fixed by handoff/CLAUDE_CODE_CLI_PROMPT_P1_SEGMENT_TRUSS_2026-10-12.md T3.
REGISTRY_COLUMNS = ("plant_id", "axis", "above_rank", "first_observed", "note")
SEGMENT_STATUS = "derived"


class TrussRegistryError(ValueError):
    """The truss registry breaks its own rules; reported, never repaired (CONVENTIONS section 4)."""


@dataclass(frozen=True)
class TrussEntry:
    plant_id: str
    axis: str
    above_rank: int | None  # None = position on the axis not recorded
    first_observed: date
    serial: int  # per plant, registry row order (rows are appended in observation order)
    row_ref: str

    def vertex_id(self) -> str:
        """``<plant_id>/F<4-digit serial>``: creation order, never a rank or position (MTG section 4)."""
        return f"{self.plant_id}/F{self.serial:04d}"


def _date(text: str, where: str) -> date:
    try:
        return date.fromisoformat(text.strip())
    except ValueError as exc:
        raise TrussRegistryError(f"{where}: {text!r} is not an ISO date (YYYY-MM-DD)") from exc


def read_registry(path: Path) -> list[TrussEntry]:
    """Read and validate the truss registry. Every violated rule raises; nothing is filled in."""
    path = Path(path)
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != REGISTRY_COLUMNS:
            raise TrussRegistryError(f"{path.name}: header {reader.fieldnames} != {REGISTRY_COLUMNS}")
        rows = list(reader)
    s.check_no_primes(rows, path.name)
    out: list[TrussEntry] = []
    serial: dict[str, int] = {}
    last_day: dict[str, date] = {}
    placed: set[tuple[str, str, int]] = set()
    for i, r in enumerate(rows, start=2):
        where = f"{path.name} line {i}"
        s.check_identifier(r["plant_id"], "plant_id")
        axis = r["axis"].strip()
        if s.ORDER2_AXIS_RE.match(axis):
            raise TrussRegistryError(f"{where}: axis {axis!r}: {s.ORDER2_RESERVED}")
        if not s.AXIS_RE.match(axis):
            raise TrussRegistryError(f"{where}: axis {axis!r} must be M or S<k>")
        text = r["above_rank"].strip()
        if text in ("", UNAVAILABLE):
            above = None
        else:
            try:
                above = int(text)
            except ValueError:
                raise TrussRegistryError(f"{where}: above_rank {text!r} is not an integer") from None
            if (r["plant_id"], axis, above) in placed:
                raise TrussRegistryError(f"{where}: a second truss above leaf rank {above} on {axis}")
            placed.add((r["plant_id"], axis, above))
        day = _date(r["first_observed"], where)
        if r["plant_id"] in last_day and day < last_day[r["plant_id"]]:
            raise TrussRegistryError(
                f"{where}: first_observed {day} is earlier than the row above for {r['plant_id']}; append rows in "
                "observation order (the truss serial is the row order and must never change)")
        last_day[r["plant_id"]] = day
        serial[r["plant_id"]] = serial.get(r["plant_id"], 0) + 1
        out.append(TrussEntry(r["plant_id"], axis, above, day, serial[r["plant_id"]], f"{path.name}#line{i}"))
    return out


def check_against_axes(entries: Sequence[TrussEntry], side_entries: Sequence[RegistryEntry],
                       plant_ids: Sequence[str] | None = None) -> None:
    """A truss on S<k> needs that side shoot in the side-shoot registry, recorded no later than the truss."""
    side = {(e.plant_id, e.axis): e for e in side_entries}
    for t in entries:
        if plant_ids is not None and t.plant_id not in plant_ids:
            continue
        if t.axis == "M":
            continue
        e = side.get((t.plant_id, t.axis))
        if e is None:
            raise TrussRegistryError(f"{t.row_ref}: truss on {t.plant_id} {t.axis}, which has no side-shoot "
                                     "registry entry (A4: an S-axis exists only when registered)")
        if t.first_observed < e.first_observed:
            raise TrussRegistryError(f"{t.row_ref}: truss first_observed {t.first_observed} before its axis "
                                     f"{t.axis} was registered ({e.first_observed})")


def write_template(folder: Path) -> Path:
    """Header + one clearly marked example row + README, for the human to copy to data/records/trusses/."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "truss_registry.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(REGISTRY_COLUMNS)
        w.writerow(["dwt_101", "M", "6", "2026-10-12",
                    "EXAMPLE ROW - delete before use; first truss of the main stem, directly above main leaf rank 6"])
    (folder / "README.md").write_text(
        "# Truss registry (human-written; MTG Amendment A5)\n\n"
        "Copy `truss_registry.csv` to `data/records/trusses/truss_registry.csv` and delete the example row.\n"
        "One row per truss. **Append new rows at the bottom in the order you see the trusses** (per plant the "
        "dates must not go backwards): the software numbers trusses by row order and that number must never "
        "change.\n\n"
        "| column | meaning |\n|---|---|\n"
        "| plant_id | e.g. dwt_101 |\n"
        "| axis | `M` (main stem, including the stem that continues above a truss) or `S1`, `S2`, ... (a registered "
        "side shoot). Never use prime characters. |\n"
        "| above_rank | rank, on that same axis, of the leaf directly below the truss (the truss sits above it); "
        "blank if unknown |\n"
        "| first_observed | date (YYYY-MM-DD) the truss was first seen |\n"
        "| note | free text |\n\n"
        "You never enter `segment_index`: the software derives it from this file and the leaf ranks (segment 1 "
        "below the first truss, 2 between the first and second, ...). A truss on a side shoot needs that side "
        "shoot in `data/records/side_shoots/side_shoot_registry.csv` first. The axis is never split above a "
        "truss: the main stem stays `M` and its leaf ranks run on.\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------------------
# Per-capture rows
# --------------------------------------------------------------------------------------


def _first_capture(clock: Sequence[CaptureClock], day: date) -> int | None:
    for i, c in enumerate(clock):
        if c.when is not None and c.when.date() >= day:
            return i
    return None


def known_at(entries: Sequence[TrussEntry], plant_id: str, clock: Sequence[CaptureClock],
             capture_id: str) -> list[TrussEntry]:
    """Trusses of the plant recorded on or before this capture's date (no look-ahead)."""
    cap = next(c for c in clock if c.capture_id == capture_id)
    if cap.when is None:
        return []
    return [t for t in entries if t.plant_id == plant_id and t.first_observed <= cap.when.date()]


def segment_of(position: tuple[int, int], placed: Sequence[int]) -> int:
    """1 + trusses strictly below ``position`` ((rank, 0) for a leaf, (above_rank, 1) for a truss)."""
    return 1 + sum(1 for a in placed if (a, 1) < position)


def _axis_trusses(now: Sequence[TrussEntry], axis: str) -> tuple[list[TrussEntry], list[int], bool]:
    on_axis = [t for t in now if t.axis == axis]
    placed = [t.above_rank for t in on_axis if t.above_rank is not None]
    return on_axis, placed, len(placed) == len(on_axis)


def truss_table_rows(plant_instance_id: str, plant_id: str, clock: Sequence[CaptureClock],
                     entries: Sequence[TrussEntry], axis_vertex_of: Mapping[str, str], evidence: str,
                     registry_status: str) -> list[dict[str, str]]:
    """``trusses.csv``: one row per (capture, truss) from the capture of its first record on."""
    rows = []
    for cap in clock:
        now = known_at(entries, plant_id, clock, cap.capture_id)
        for t in now:
            _, placed, all_placed = _axis_trusses(now, t.axis)
            seg = (str(segment_of((t.above_rank, 1), placed)) if t.above_rank is not None and all_placed
                   else UNAVAILABLE)
            first_i = _first_capture(clock, t.first_observed)
            exact = first_i is not None and clock[first_i].when is not None and \
                clock[first_i].when.date() == t.first_observed
            start = clock[first_i - 1].capture_id if exact and first_i > 0 else UNAVAILABLE
            end = clock[first_i].capture_id if first_i is not None else UNAVAILABLE
            pr = UNAVAILABLE if t.above_rank is None else str(t.above_rank)
            rows.append(dict(
                plant_instance_id=plant_instance_id, capture_id=cap.capture_id, truss_vertex_id=t.vertex_id(),
                axis_id=t.axis, axis_vertex_id=axis_vertex_of.get(t.axis, UNAVAILABLE), parent_rank=pr,
                parent_rank__status=UNAVAILABLE if pr == UNAVAILABLE else registry_status, segment_index=seg,
                segment_index__status=UNAVAILABLE if seg == UNAVAILABLE else SEGMENT_STATUS,
                first_observed_date=t.first_observed.isoformat(),
                first_observed_capture_id=clock[first_i].capture_id if exact else UNAVAILABLE,
                emergence_interval_start=start, emergence_interval_end=end,
                source_kind="user_stated" if registry_status == "user_stated" else "fixture_declared",
                source_ref="truss_registry " + t.row_ref, registry_ref=t.row_ref, evidence=evidence))
    return rows


def annotate_axes(axes_rows: list[dict[str, str]], entries: Sequence[TrussEntry] | None, plant_id: str,
                  plant_instance_id: str, clock: Sequence[CaptureClock]) -> None:
    """``axes.csv`` A5 columns: ``truss_count`` and apical ``segment_index`` (= truss_count + 1) per capture.
    ``entries is None`` (no registry) -> unavailable."""
    for row in axes_rows:
        if row["plant_instance_id"] != plant_instance_id:
            continue
        if entries is None:
            row.update(segment_index=UNAVAILABLE, segment_index__status=UNAVAILABLE, truss_count=UNAVAILABLE)
            continue
        now = known_at(entries, plant_id, clock, row["capture_id"])
        count = sum(1 for t in now if t.axis == row["axis"])
        row.update(segment_index=str(count + 1), segment_index__status=SEGMENT_STATUS, truss_count=str(count))


def truss_vertex_rows(template: Mapping[str, str], now: Sequence[TrussEntry], axis_vertex_of: Mapping[str, str],
                      registry_status: str) -> list[dict[str, str]]:
    """Scale-3 ``Truss`` MTG vertices for one snapshot. ``template`` is the snapshot's Plant row (identity
    columns are copied from it). No geometry: every geometric value stays unavailable."""
    out = []
    for t in now:
        row = s.blank_mtg_row()
        for col in ("plant_instance_id", "plant_id", "capture_id", "snapshot_capture_id", "frame", "evidence"):
            row[col] = template[col]
        row.update(vertex_id=t.vertex_id(), scale="3", axis=t.axis,
                   complex_id=axis_vertex_of.get(t.axis, UNAVAILABLE), parent_id=UNAVAILABLE, edge_type="+",
                   display_name=UNAVAILABLE, observed="false", **{"class": s.TRUSS_CLASS})
        s.set_value(row, "order", "0" if t.axis == "M" else "1", "derived")
        if t.above_rank is not None:
            s.set_value(row, "parent_rank", str(t.above_rank), registry_status)
        out.append(row)
    return out


def apply_segments(rows: list[dict[str, str]], now: Sequence[TrussEntry] | None) -> None:
    """Fill ``segment_index`` on the Axis, CompoundLeaf, Truss and leaflet rows of ONE snapshot (in place).

    ``now`` = the trusses known at this capture, or None when no registry exists (all stay unavailable)."""
    if now is None:
        return
    by_axis_rows: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        if r["axis"] != UNAVAILABLE:
            by_axis_rows.setdefault(r["axis"], []).append(r)
    seg_of_vertex: dict[str, str] = {}
    for axis, members in by_axis_rows.items():
        on_axis, placed, all_placed = _axis_trusses(now, axis)
        for r in members:
            if r["class"] == "Axis":
                s.set_value(r, "segment_index", str(1 + len(on_axis)), SEGMENT_STATUS)
            elif r["class"] == "CompoundLeaf" and r["rank"] != UNAVAILABLE and all_placed:
                s.set_value(r, "segment_index", str(segment_of((int(r["rank"]), 0), placed)), SEGMENT_STATUS)
            elif r["class"] == s.TRUSS_CLASS and r["parent_rank"] != UNAVAILABLE and all_placed:
                s.set_value(r, "segment_index", str(segment_of((int(r["parent_rank"]), 1), placed)), SEGMENT_STATUS)
            seg_of_vertex[r["vertex_id"]] = r["segment_index"]
    for scale in ("4", "5"):  # organs of a compound (petiole, rachis, leaflets), then secondary leaflets
        for r in rows:
            if r["scale"] == scale and r["axis"] != UNAVAILABLE and \
                    seg_of_vertex.get(r["complex_id"], UNAVAILABLE) != UNAVAILABLE:
                s.set_value(r, "segment_index", seg_of_vertex[r["complex_id"]], SEGMENT_STATUS)
                seg_of_vertex[r["vertex_id"]] = r["segment_index"]


def fill_identity_segments(identity_rows: list[dict[str, str]], snapshots: Sequence[Mapping[str, str]]) -> None:
    """``identity_manifest.csv`` ``segment_index`` = the snapshot value of that organ at that capture
    (a terminal leaflet ``<compound>/T`` repeats its compound's)."""
    seg = {(r["plant_instance_id"], r["capture_id"], r["vertex_id"]): r["segment_index"] for r in snapshots}
    for r in identity_rows:
        key = (r["plant_instance_id"], r["capture_id"], r["organ_id"])
        value = seg.get(key, UNAVAILABLE)
        if value == UNAVAILABLE and r["organ_id"].endswith("/T"):
            value = seg.get((r["plant_instance_id"], r["capture_id"], r["organ_id"][:-2]), UNAVAILABLE)
        r["segment_index"] = value
