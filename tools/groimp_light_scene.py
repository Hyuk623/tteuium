"""Phase 2 of the XL light-simulation plan: a real tomato snapshot in a GroIMP light scene, sensor planes only (2026-09-29).

    python -X utf8 -m tools.groimp_light_scene --handoff build/xl_handoff_<run> --plant dwt_02 --out build/groimp_light_scene_<date>

Plan: handoff/CLAUDE_XL_LIGHT_SIMULATION_ADOPTION_2026-09-29.md, answers in CLAUDE_XL_LIGHT_REVIEW_ANSWERS_2026-09-29.md.
A copy of the plant's static XL export (Model.rgg; the export itself is not changed) gets a point lamp, a grid of black
sensor plates on the board plane and a `measure()` method. The same lamp and sensors are also computed without the plant
and by tomato3d.light.raytrace.direct_light. Reported per sensor:

* incident photon rate on the plate (umol s-1) in the plant scene and in the empty scene (GroIMP), and the python value;
* relative_incident = plant scene / empty scene (unit 1): the only light quantity this phase claims.

Every organ of the plant graph is listed with calculation_status `not_a_surface`: the exports hold position markers and
axes, not leaf surfaces, so no per-organ light is computed (Phase 3 needs reviewed meshes). The lamp position is an
ASSUMED placeholder above the plant until config/light_scene.json is measured; absolute PPFD stays unavailable.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import time
from pathlib import Path

import numpy as np

from tools.groimp_light_sanity import CORE, run_groimp
from tools.leaf_light.common import StudyError, file_hash, output_dir, read_json, write_json

FLUX = 1000.0  # umol s-1, relative test value
LAMP_ABOVE_TOP_M = 0.25
SENSOR_M, SENSOR_THICK_M, SENSOR_PITCH_M, GRID = 0.03, 0.0002, 0.05, 5
MODULES = ('Plant', 'MainStem', 'CompoundLeaf', 'SubStem', 'Leaflet', 'GrowthShoot')

LIGHT_HEADER = """import de.grogra.ray.physics.Spectrum;
// ---- light scene added by tools.groimp_light_scene (Phase 2); the plant graph below is the unchanged export ----
module Sensor(int sid) extends Box({thick}f, {size}f, {size}f);
module Lamp extends LightNode;
LightModel lm = new LightModel({rays}, 1);
"""
MEASURE = """
public void measure()
{{
    lm.compute();
    for (Sensor r : (* Sensor *)) {{
        Spectrum s = lm.getAbsorbedPower(r);
        println("SENSOR\\t" + r.sid + "\\t" + s.integrate());
    }}
{counts}
    println("SANITY_DONE");
}}
"""


def plant_extent(export: Path) -> tuple[np.ndarray, float]:
    xyz = []
    with open(export / 'coordinates.csv', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            xyz.append([float(r['x_m']), float(r['y_m']), float(r['z_m'])])
    xyz = np.array(xyz)
    if not len(xyz):
        raise StudyError('The export has no coordinates to place the lamp over')
    return xyz[:, :2].mean(0), float(xyz[:, 2].max())


def sensors(center: np.ndarray) -> list[tuple[int, float, float]]:
    off = (np.arange(GRID) - (GRID - 1) / 2) * SENSOR_PITCH_M
    return [(i * GRID + j, float(center[0] + dx), float(center[1] + dy)) for i, dx in enumerate(off) for j, dy in enumerate(off)]


def scene_rgg(base: str | None, lamp: np.ndarray, grid, rays: int) -> str:
    lamp_node = f'[ Translate({lamp[0]:.5f}f, {lamp[1]:.5f}f, {lamp[2]:.5f}f) Lamp().(setLight(new PointLight().(setPower({FLUX}f)))) ]'
    sens = ' '.join(f'[ Translate({x:.5f}f, {y:.5f}f, 0) Sensor({i}).(setShader(BLACK)) ]' for i, x, y in grid)
    header = LIGHT_HEADER.format(thick=SENSOR_THICK_M, size=SENSOR_M, rays=rays)
    if base is None:  # empty scene: lamp and sensors only
        body = f'protected void init()\n[\n    Axiom ==> {lamp_node} {sens};\n]\n'
        return header + body + MEASURE.format(counts='')
    if base.count('Axiom ==>') != 1:
        raise StudyError('Unexpected export: expected exactly one "Axiom ==>" production')
    body = base.replace('Axiom ==>', f'Axiom ==> {lamp_node} {sens}', 1)
    # imports must precede every declaration: put the light declarations after the export's last import line
    lines = body.split('\n')
    last = max((k for k, line in enumerate(lines) if line.startswith('import ')), default=-1)
    body = '\n'.join(lines[:last + 1] + [header] + lines[last + 1:])
    counts = '\n'.join(f'    println("COUNT {m}=" + count((* {m} *)));' for m in MODULES)
    return body + MEASURE.format(counts=counts)


def python_sensors(lamp: np.ndarray, grid) -> dict:
    from tools.groimp_light_sanity import python_module  # same face sampling and direct-light call as Phase 1
    import tools.groimp_light_sanity as gls
    out, saved = {}, (gls.LAMP_HEIGHT_M, gls.PLATE_M, gls.THICK_M, gls.FLUX)
    try:
        gls.LAMP_HEIGHT_M, gls.PLATE_M, gls.THICK_M, gls.FLUX = float(lamp[2]), SENSOR_M, SENSOR_THICK_M, FLUX
        for i, x, y in grid:
            out[i] = python_module(math.hypot(x - lamp[0], y - lamp[1]))['absorbed_umol_s']
    finally:
        gls.LAMP_HEIGHT_M, gls.PLATE_M, gls.THICK_M, gls.FLUX = saved
    return out


def build(handoff: Path, plant: str, out: Path, rays: int = 20_000_000, core: Path = CORE) -> dict:
    export = Path(handoff) / plant / 'export'
    manifest = read_json(export / 'export.json')
    if file_hash(export / 'Model.rgg') != manifest['model_sha256']:
        raise StudyError('Model.rgg changed since export')
    out = output_dir(Path(out))
    center, top = plant_extent(export)
    lamp = np.array([center[0], center[1], top + LAMP_ABOVE_TOP_M])
    grid = sensors(center)
    runs = {}
    for name, base in (('empty', None), ('plant', (export / 'Model.rgg').read_text(encoding='utf-8'))):
        d = out / name
        d.mkdir()
        (d / 'Model.rgg').write_text(scene_rgg(base, lamp, grid, rays), encoding='utf-8')
        t0 = time.time()
        _, _ = None, None
        text = _run(d, core)
        runs[name] = dict(sensors={int(i): float(v) for i, v in __import__('re').findall(r'SENSOR\t(\d+)\t([0-9.eE+-]+)', text)},
                          counts={k: int(v) for k, v in __import__('re').findall(r'COUNT (\w+)=(\d+)', text)},
                          seconds=round(time.time() - t0, 1), model_sha256=file_hash(d / 'Model.rgg'))
    py = python_sensors(lamp, grid)
    scenario = f'phase2_{plant}_assumed_lamp'
    rows = []
    for i, x, y in grid:
        e, p = runs['empty']['sensors'][i], runs['plant']['sensors'][i]
        base = dict(scenario_id=scenario, plant_id=plant, session_id=manifest.get('session_id'), organ_key=f'sensor/{i}',
                    geometry_source='sensor_plate_black', surface_or_sensor_plane=f'board plane z=0, centre ({x:.3f}, {y:.3f}) m',
                    backend='GroIMP LightModel CPU', calculation_status='computed')
        rows.append(dict(base, quantity='incident_photon_rate_plant_scene', unit='umol s-1', value=p, notes='lamp assumed'))
        rows.append(dict(base, quantity='incident_photon_rate_empty_scene', unit='umol s-1', value=e, notes='lamp assumed'))
        rows.append(dict(base, quantity='incident_photon_rate_python', unit='umol s-1', value=py[i], backend='tomato3d.light.raytrace',
                         notes='empty scene, analytic-equivalent'))
        rows.append(dict(base, quantity='relative_incident', unit='1', value=p / e if e > 0 else float('nan'),
                         notes='plant scene / empty scene; the only light quantity claimed in Phase 2'))
    with open(export / 'organs.csv', encoding='utf-8') as fh:
        for o in csv.DictReader(fh):
            if o.get('module') in MODULES:
                rows.append(dict(scenario_id=scenario, plant_id=plant, session_id=manifest.get('session_id'), organ_key=o['key'],
                                 geometry_source='diagnostic_marker_or_axis', quantity='incident_photon_rate', unit='umol s-1',
                                 value='', surface_or_sensor_plane='', backend='', calculation_status='not_a_surface',
                                 notes='no reviewed leaf surface in the export; Phase 3 needs meshes'))
    fields = ['scenario_id', 'plant_id', 'session_id', 'organ_key', 'geometry_source', 'quantity', 'unit', 'value',
              'surface_or_sensor_plane', 'calculation_status', 'backend', 'notes']
    with open(out / 'light_results.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    rel = np.array([runs['plant']['sensors'][i] / runs['empty']['sensors'][i] for i, _, _ in grid])
    gro_vs_py = np.array([runs['empty']['sensors'][i] / py[i] - 1 for i, _, _ in grid])
    exp_counts = {}
    with open(export / 'organs.csv', encoding='utf-8') as fh:
        for o in csv.DictReader(fh):
            exp_counts[o.get('module')] = exp_counts.get(o.get('module'), 0) + 1
    checks = dict(organ_counts_match_export=all(runs['plant']['counts'].get(m) == exp_counts.get(m, 0) for m in MODULES),
                  every_sensor_reported=len(runs['plant']['sensors']) == len(grid) == len(runs['empty']['sensors']),
                  empty_scene_within_5pct_of_python=bool(np.all(np.abs(gro_vs_py) < 0.05)))
    doc = dict(schema='groimp-light-scene-1', phase=2, status='passed' if all(checks.values()) else 'failed', checks=checks,
               plant_id=plant, source_export=str(export), source_model_sha256=manifest['model_sha256'],
               lamp_board_frame_m=lamp.round(4).tolist(), lamp_status='assumed placeholder (no measured light scene yet)',
               flux_umol_s=FLUX, rays=rays, sensors=dict(grid=GRID, size_m=SENSOR_M, pitch_m=SENSOR_PITCH_M, plane='board z=0'),
               relative_incident=dict(min=round(float(rel.min()), 4), max=round(float(rel.max()), 4), mean=round(float(rel.mean()), 4)),
               groimp_empty_vs_python=dict(min=round(float(gro_vs_py.min()), 4), max=round(float(gro_vs_py.max()), 4)),
               organ_counts=runs['plant']['counts'], runs={k: {kk: vv for kk, vv in v.items() if kk != 'sensors'} for k, v in runs.items()},
               groimp_version='2.2.1', core_sha256=file_hash(core), frame='board frame, metres, +Z up (as the export)',
               validated_metric=False, suitable_for_ppfd=False,
               note='software/scene check: the plant has only markers and axes, so shading is near zero by construction')
    write_json(out / 'manifest.json', doc)
    return doc


def _run(project: Path, core: Path) -> str:
    """run_groimp of Phase 1 parses its own RESULT lines; here the raw log text is returned."""
    try:
        run_groimp(project, core)
    except StudyError:
        pass
    text = (project / 'groimp.log').read_text(encoding='utf-8', errors='replace')
    if 'SANITY_DONE' not in text:
        raise StudyError(f'measure() did not run; see {project / "groimp.log"}')
    return text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--handoff', required=True, type=Path)
    ap.add_argument('--plant', required=True)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--rays', type=int, default=20_000_000)
    a = ap.parse_args()
    d = build(a.handoff, a.plant, a.out, a.rays)
    print(json.dumps({k: d[k] for k in ('status', 'checks', 'relative_incident', 'groimp_empty_vs_python', 'organ_counts', 'runs')},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
