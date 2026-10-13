"""Shared existing fixture schedule and photon-dose arithmetic; no transport."""
from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Any
from zoneinfo import ZoneInfo

from tomato3d.io.schemas import ScheduleSegment
from tools.leaf_light.common import StudyError


def _schedules(schedule: dict) -> tuple[ZoneInfo, dict]:
    if schedule.get('fixed_optics_beam_spectrum') is not True:
        raise StudyError('explicit_fixed_response_assumption_required')
    if not schedule.get('provenance'):
        raise StudyError('schedule_provenance_required')
    zone = ZoneInfo(schedule['timezone']); parsed = {}
    for fixture, segments in schedule['fixtures'].items():
        if fixture == 'all':
            raise StudyError('schedule_requires_actual_fixture_ids')
        if segments is None:
            parsed[fixture] = None; continue
        if not segments:
            raise StudyError('empty_schedule_is_unknown_use_explicit_zero_segment')
        windows = []
        for raw in segments:
            segment = ScheduleSegment.model_validate(raw)
            windows.extend((a, b, segment.output_fraction) for a, b in segment.day_intervals_minutes())
        windows.sort()
        if any(a[1] > b[0] for a, b in zip(windows, windows[1:])):
            raise StudyError('overlapping_fixture_schedule')
        parsed[fixture] = windows
    return zone, parsed


def _fraction(moment: datetime, zone: ZoneInfo, windows: list | None) -> float | None:
    if windows is None:
        return None
    local = moment.astimezone(zone); minute = local.hour * 60 + local.minute
    return next((fraction for a, b, fraction in windows if a <= minute < b), 0.)


def schedule_boundaries(start: datetime, end: datetime, zone: ZoneInfo, fixtures: dict,
                        max_schedule_minutes: int) -> set[datetime]:
    """Shared HH:MM boundary scan for tissue and reference light, using elapsed UTC."""
    minutes = math.ceil((end - start).total_seconds() / 60) + 1
    if type(max_schedule_minutes) is not int or max_schedule_minutes < minutes:
        raise StudyError('schedule_scan_budget_exceeded')
    cuts = {start, end}
    tick = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
    previous = tuple(_fraction(start, zone, w) for w in fixtures.values())
    while tick < end:
        signature = tuple(_fraction(tick, zone, w) for w in fixtures.values())
        if signature != previous or tick.astimezone(zone).time().isoformat() == '00:00:00':
            cuts.add(tick)
        previous = signature; tick += timedelta(minutes=1)
    return cuts


def photon_integral(value_seconds: Any) -> float:
    """Shared umol -> mol integral; callers own explicit support/coverage validation."""
    return math.fsum(value * seconds for value, seconds in value_seconds) * 1e-6


