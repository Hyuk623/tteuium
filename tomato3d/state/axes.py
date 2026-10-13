"""Axes and side shoots (MTG Amendment A4): human registry, axes.csv, cluster classification.

User decisions of 2026-10-12 (``user_stated``):

* a side shoot first appears with **two leaves together**; it is registered as an ``axis_shoot``
  (order-1 axis), ``first_observed`` = that capture, emergence interval = (previous capture, this capture];
* it becomes a ``substem`` when its first two leaves are fully expanded; its apex bundle is then shown as
  ``shoot′`` (S1), ``shoot″`` (S2)...; the main apex bundle stays ``shoot``. Primes are display-only;
* ranks are counted on every axis by the same unfolding rule and never renumbered; a tie of the first two
  leaves of a side axis -> the basal leaf is rank 1 (proposal in A4, **confirmed by the user 2026-10-12**, A5);
* side-shoot numbering = registration order, immutable, same capture -> lower node first (proposal in A4,
  **confirmed 2026-10-12**, A5); a sympodial continuation above a truss is main stem (M), never a substem;
  a truss bears no leaves, so the two-leaf rule already excludes it (trusses: :mod:`tomato3d.state.trusses`);
* order-2 side shoots: notation reserved as ``S1.1`` (A5); code still rejects them;
* ``topology_scope = provided_axes``: unobserved side shoots are never generated.

The registry ``data/records/side_shoots/side_shoot_registry.csv`` is human-owned and read-only; it is the only
source of ``parent_rank`` from top views. A template is shipped under ``build/`` (never into data/records/).
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import schema as s

REGISTRY_PATH = Path("data/records/side_shoots/side_shoot_registry.csv")
#: Prompt S3 columns + ``state_date`` (the date the row's ``axis_state`` was recorded), needed to place the
#: axis_shoot -> substem change at a capture. One row per (plant, axis, state); rows are a state history.
REGISTRY_COLUMNS = ("plant_id", "axis", "parent_rank", "first_observed", "axis_state", "state_date", "note")
REGISTRY_STATES = ("axis_shoot", "substem")


class RegistryError(ValueError):
    """The registry breaks its own rules; reported, never repaired (CONVENTIONS section 4)."""


@dataclass(frozen=True)
class RegistryEntry:
    plant_id: str
    axis: str
    parent_rank: int | None
    first_observed: date
    states: tuple[tuple[date, str], ...]  # (state_date, axis_state), chronological
    row_refs: tuple[str, ...]


def _date(text: str, where: str) -> date:
    try:
        return date.fromisoformat(text.strip())
    except ValueError as exc:
        raise RegistryError(f"{where}: {text!r} is not an ISO date (YYYY-MM-DD)") from exc


def read_registry(path: Path) -> list[RegistryEntry]:
    """Read and validate the registry. Every violated rule raises; nothing is filled in."""
    with Path(path).open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != REGISTRY_COLUMNS:
            raise RegistryError(f"{path.name}: header {reader.fieldnames} != {REGISTRY_COLUMNS}")
        rows = list(reader)
    s.check_no_primes(rows, path.name)
    grouped: dict[tuple[str, str], list[tuple[int, dict[str, str]]]] = {}
    for i, r in enumerate(rows, start=2):
        where = f"{path.name} line {i}"
        if s.ORDER2_AXIS_RE.match(r["axis"]):
            raise RegistryError(f"{where}: axis {r['axis']!r}: {s.ORDER2_RESERVED}")
        if not s.AXIS_RE.match(r["axis"]) or r["axis"] == "M":
            raise RegistryError(f"{where}: axis {r['axis']!r} must be S<k> (the main stem M is not registered)")
        if r["axis_state"] not in REGISTRY_STATES:
            raise RegistryError(f"{where}: axis_state {r['axis_state']!r} not in {REGISTRY_STATES}")
        s.check_identifier(r["plant_id"], "plant_id")
        grouped.setdefault((r["plant_id"], r["axis"]), []).append((i, r))
    out = []
    for (plant, axis), items in sorted(grouped.items()):
        first = {_date(r["first_observed"], f"{path.name} line {i}") for i, r in items}
        if len(first) != 1:
            raise RegistryError(f"{plant} {axis}: first_observed differs between rows {sorted(first)}")
        pr = {r["parent_rank"].strip() for _, r in items}
        if len(pr) != 1:
            raise RegistryError(f"{plant} {axis}: parent_rank differs between rows {sorted(pr)}")
        pr_text = pr.pop()
        parent_rank = None if pr_text in ("", UNAVAILABLE) else int(pr_text)
        states = sorted((_date(r["state_date"] or r["first_observed"], f"{path.name} line {i}"), r["axis_state"])
                        for i, r in items)
        # a shoot first recorded already expanded (registered late) may start as substem
        seen_substem = False
        for d, st in states:
            if d < next(iter(first)):
                raise RegistryError(f"{plant} {axis}: state date {d} before first_observed")
            if st == "axis_shoot" and seen_substem:
                raise RegistryError(f"{plant} {axis}: substem -> axis_shoot is not a defined change")
            seen_substem |= st == "substem"
        out.append(RegistryEntry(plant, axis, parent_rank, next(iter(first)), tuple(states),
                                 tuple(f"{path.name}#line{i}" for i, _ in items)))
    _check_numbering(out)
    return out


def _check_numbering(entries: Sequence[RegistryEntry]) -> None:
    """Numbering basis (user_stated, A5 16.1): S-indices follow registration order per plant; same date -> lower
    node first. A registry that numbers otherwise is reported, not renumbered."""
    by_plant: dict[str, list[RegistryEntry]] = {}
    for e in entries:
        by_plant.setdefault(e.plant_id, []).append(e)
    for plant, es in by_plant.items():
        ordered = sorted(es, key=lambda e: (e.first_observed, e.parent_rank if e.parent_rank is not None else 10 ** 6,
                                            int(e.axis[1:])))
        expected = [f"S{k}" for k in range(1, len(ordered) + 1)]
        if [e.axis for e in ordered] != expected:
            raise RegistryError(f"{plant}: axes {[e.axis for e in ordered]} do not follow registration order "
                                f"{expected} ({s.NUMBERING_BASIS})")


def write_template(folder: Path) -> Path:
    """Header + one clearly marked example row, for the human to copy to data/records/side_shoots/."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "side_shoot_registry.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(REGISTRY_COLUMNS)
        w.writerow(["dwt_101", "S1", "2", "2026-10-12", "axis_shoot", "2026-10-12",
                    "EXAMPLE ROW - delete before use; two leaves seen together in the axil of main-stem leaf rank 2"])
    (folder / "README.md").write_text(
        "# Side-shoot registry (human-written; MTG Amendment A4)\n\n"
        "Copy `side_shoot_registry.csv` to `data/records/side_shoots/side_shoot_registry.csv` and delete the example row.\n"
        "One row per side shoot and recorded state; add a new row (same first_observed, parent_rank) when it becomes a substem.\n\n"
        "| column | meaning |\n|---|---|\n"
        "| plant_id | e.g. dwt_101 |\n"
        "| axis | S1, S2, ... in registration order (same day: lower node first). Never use prime characters. |\n"
        "| parent_rank | rank of the MAIN-stem leaf in whose axil the shoot sits; blank if unknown |\n"
        "| first_observed | date (YYYY-MM-DD) the two leaves were first seen together |\n"
        "| axis_state | axis_shoot (just appeared) or substem (first two leaves fully expanded) |\n"
        "| state_date | date this axis_state was observed |\n"
        "| note | free text |\n\n"
        "Display labels 1, 1′, 1″ are produced by the software; files store axis codes only. A sympodial "
        "continuation above a truss is the main stem, never a side shoot. Trusses go in the separate truss "
        "registry (`data/records/trusses/truss_registry.csv`).\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------------------
# axes.csv rows
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CaptureClock:
    capture_id: str
    when: datetime | None  # None = capture time unavailable


def _capture_on_or_after(clock: Sequence[CaptureClock], day: date) -> int | None:
    for i, c in enumerate(clock):
        if c.when is not None and c.when.date() >= day:
            return i
    return None


def axes_rows(plant_instance_id: str, plant_id: str, clock: Sequence[CaptureClock],
              entries: Sequence[RegistryEntry], parent_node_of_rank: Mapping[int, str], evidence: str,
              registry_status: str, registration_leaves: Mapping[str, Sequence[str]] | None = None
              ) -> list[dict[str, str]]:
    """One row per (capture, axis): M always; each registered S-axis from the capture of its first observation.

    Registry date -> capture: the first capture of the plant on or after that date. A registry date before the
    first capture gives ``first_observed_capture_id = unavailable`` and an emergence interval (unavailable, first
    capture]. ``registry_status`` is ``user_stated`` for the human registry and ``synthetic_truth`` for a fixture."""
    rows: list[dict[str, str]] = []
    mine = [e for e in entries if e.plant_id == plant_id]
    for ci, cap in enumerate(clock):
        rows.append(_row(plant_instance_id, cap.capture_id, "M", f"{plant_id}/A0", "0", "", UNAVAILABLE,
                         s.MAIN_AXIS_PARENT_RANK, "derived", "main", UNAVAILABLE, UNAVAILABLE, UNAVAILABLE,
                         UNAVAILABLE, UNAVAILABLE, UNAVAILABLE, "definition:main_axis", "derived",
                         "MTG A4: the main stem incl. sympodial continuation", evidence))
        for e in mine:
            first_i = _capture_on_or_after(clock, e.first_observed)
            if cap.when is None or cap.when.date() < e.first_observed:
                continue
            state = "axis_shoot"
            since_day = e.first_observed
            for d, st in e.states:
                if d <= cap.when.date():
                    state, since_day = st, d
            since_i = _capture_on_or_after(clock, since_day)
            exact_first = first_i is not None and clock[first_i].when is not None and \
                clock[first_i].when.date() == e.first_observed
            first_id = clock[first_i].capture_id if exact_first else UNAVAILABLE
            if exact_first:
                start = clock[first_i - 1].capture_id if first_i and first_i > 0 else UNAVAILABLE
                end = clock[first_i].capture_id
            else:
                start, end = UNAVAILABLE, (clock[first_i].capture_id if first_i is not None else UNAVAILABLE)
            pr = UNAVAILABLE if e.parent_rank is None else str(e.parent_rank)
            leaves = (registration_leaves or {}).get(e.axis, [])
            rows.append(_row(
                plant_instance_id, cap.capture_id, e.axis, f"{plant_id}/{e.axis}", "1", "M",
                parent_node_of_rank.get(e.parent_rank, UNAVAILABLE) if e.parent_rank is not None else UNAVAILABLE,
                pr, UNAVAILABLE if pr == UNAVAILABLE else registry_status, state,
                clock[since_i].capture_id if since_i is not None else UNAVAILABLE, first_id, e.first_observed.isoformat(),
                start, end, ";".join(leaves) if leaves else UNAVAILABLE, ";".join(e.row_refs),
                registry_status if registry_status != "synthetic_truth" else "fixture_declared",
                "side_shoot_registry " + ";".join(e.row_refs), evidence))
    return rows


def _row(pid: str, capture: str, axis: str, vertex: str, order: str, parent_axis: str, parent_node: str,
         parent_rank: str, parent_rank_status: str, state: str, since: str, first_capture: str, first_date: str,
         start: str, end: str, leaves: str, reg_ref: str, source_kind: str, source_ref: str,
         evidence: str) -> dict[str, str]:
    return dict(
        plant_instance_id=pid, capture_id=capture, axis_id=axis, axis_vertex_id=vertex, order=order,
        parent_axis_id=parent_axis or UNAVAILABLE, parent_node_id=parent_node, parent_rank=parent_rank, stage=state,
        source_kind=source_kind, source_ref=source_ref, axis=axis, axis_state=state,
        parent_rank__status=parent_rank_status if parent_rank != UNAVAILABLE else UNAVAILABLE,
        axis_state_since_capture_id=since, first_observed_capture_id=first_capture, first_observed_date=first_date,
        emergence_interval_start=start, emergence_interval_end=end, registration_leaf_ids=leaves,
        registration_ref=reg_ref,
        numbering_basis=s.NUMBERING_BASIS if axis != "M" else UNAVAILABLE,
        tie_rule=s.TIE_RULE if axis != "M" else UNAVAILABLE,
        # MTG A5 columns, filled by tomato3d.state.trusses.annotate_axes (unavailable without a truss registry)
        segment_index=UNAVAILABLE, segment_index__status=UNAVAILABLE, truss_count=UNAVAILABLE, evidence=evidence)


# --------------------------------------------------------------------------------------
# S4 distinction
# --------------------------------------------------------------------------------------

CLASSIFICATION_COLUMNS = ("plant_instance_id", "capture_id", "obs_id", "obs_class", "axis_hint", "axis_hint_source",
                          "axis_state", "cluster_class", "rule")

#: detector / label class -> (obs_class, axis hint). ``sub_stem`` says "a side axis" but not which one.
DETECTOR_AXIS = {"main_stem": "M", "sub_stem": UNAVAILABLE, "growth_shoot": UNAVAILABLE}


def classify(observations: Sequence[Mapping[str, str]], state_of_axis: Mapping[str, str]) -> list[dict[str, str]]:
    """Each observed cluster -> main apex ``shoot``, side ``axis_shoot`` leaves, ``substem`` leaves, main leaves or
    ``truss``, from the explicit axis hint (human / synthetic GT / detector class) and the registry state.
    Nothing is inferred from position: without an axis hint the class is ``*_axis_unavailable``."""
    out = []
    for o in observations:
        axis = o.get("axis_hint", UNAVAILABLE)
        state = "main" if axis == "M" else state_of_axis.get(axis, UNAVAILABLE)
        cls = o["obs_class"]
        if cls == "truss":
            cluster, rule = "truss", "truss bears no leaves: never registers a side shoot (A4)"
        elif cls == "growth_shoot":
            if axis == "M":
                cluster, rule = "shoot", "main apex bundle"
            elif state == "substem":
                cluster, rule = "side_shoot_apex", "apex bundle of a substem (displayed shoot′, shoot″ ...)"
            elif state == "axis_shoot":
                cluster, rule = "axis_shoot", "the bundle is the young side shoot itself"
            else:
                cluster, rule = "growth_shoot_axis_unavailable", "no axis evidence"
        elif cls in ("compound_leaf", "terminal_leaflet", "leaflet"):
            if axis == "M":
                cluster, rule = "main_leaves", "axis hint M"
            elif state in ("axis_shoot", "substem"):
                cluster, rule = f"{state}_leaves", f"axis hint {axis} + registry state {state}"
            elif axis != UNAVAILABLE:
                cluster, rule = "side_leaves_unregistered", f"axis hint {axis} has no registry entry"
            else:
                cluster, rule = "leaves_axis_unavailable", "no axis evidence"
        elif cls == "main_stem":
            cluster, rule = "main_stem", "detector/label class main_stem -> M"
        elif cls == "sub_stem":
            cluster, rule = "side_stem", "detector/label class sub_stem -> some S-axis (index from registry/human)"
        else:
            cluster, rule = "other", cls
        out.append(dict(plant_instance_id=o["plant_instance_id"], capture_id=o["capture_id"], obs_id=o["obs_id"],
                        obs_class=cls, axis_hint=axis, axis_hint_source=o.get("axis_hint_source", UNAVAILABLE),
                        axis_state=state, cluster_class=cluster, rule=rule))
    return out


def state_of_axes(rows: Sequence[Mapping[str, str]], capture_id: str) -> dict[str, str]:
    return {r["axis"]: r["axis_state"] for r in rows if r["capture_id"] == capture_id}
