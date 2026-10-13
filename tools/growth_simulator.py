"""Environment-to-3D growth scaffold with explicitly illustrative rules.

python -m tools.growth_simulator --demo --out build/growth_demo_NEW
python -m tools.growth_simulator --input build/growth_demo_NEW/input.json --out build/growth_NEW

Synthetic organ geometry is never a reconstructed or PPFD-qualified leaf surface.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from pathlib import Path
from typing import Callable

import numpy as np

from tools.groimp_bridge import mm_to_m


def finite(name: str, value: float, low: float, high: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must be finite in [{low}, {high}]')


@dataclass(frozen=True)
class Environment:
    """Constant conditions for dt_days. PPFD is during lights-on, not 24h mean."""
    dt_days: float
    ppfd_umol_m2_s: float
    photoperiod_h: float
    temperature_c: float
    relative_humidity_pct: float
    solution_ec_ms_cm: float
    solution_ph: float
    nutrients_mg_l: dict[str, float] = field(default_factory=dict)
    water_available: bool = True

    def validate(self) -> None:
        for name, lo, hi in [('dt_days', 1e-6, 365), ('ppfd_umol_m2_s', 0, 10000),
                             ('photoperiod_h', 0, 24), ('temperature_c', -50, 80),
                             ('relative_humidity_pct', 0, 100), ('solution_ec_ms_cm', 0, 100),
                             ('solution_ph', 0, 14)]:
            finite(name, getattr(self, name), lo, hi)
        if not isinstance(self.water_available, bool):
            raise ValueError('water_available must be boolean')
        if not isinstance(self.nutrients_mg_l, dict):
            raise ValueError('nutrients_mg_l must be an element/concentration mapping')
        for name, value in self.nutrients_mg_l.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError('Nutrient names must be nonempty strings')
            finite(f'nutrients_mg_l.{name}', value, 0, 1e6)


@dataclass(frozen=True)
class Parameters:
    """All numbers must be supplied; no cultivar or optimum is inferred."""
    label: str
    light_scale_mol_m2_day: float
    temperature_centre_c: float
    temperature_halfwidth_c: float
    rh_centre_pct: float
    rh_halfwidth_pct: float
    ec_centre_ms_cm: float
    ec_halfwidth_ms_cm: float
    ph_centre: float
    ph_halfwidth: float
    node_interval_dev_days: float
    expansion_dev_days: float
    internode_mm: float
    leaf_axis_mm: float
    leaflet_length_mm: float
    leaflet_width_mm: float
    leaflet_bow_mm: float
    divergence_deg: float
    truss_after_node: int
    truss_every_nodes: int
    truss_delay_dev_days: float
    flower_delay_dev_days: float
    truss_length_mm: float
    flower_radius_mm: float
    max_nodes: int

    def validate(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError('Parameters need a provenance label')
        for name, value in asdict(self).items():
            if name == 'label':
                continue
            finite(name, value, -10000, 10000)
        positive = ['light_scale_mol_m2_day', 'temperature_halfwidth_c', 'rh_halfwidth_pct',
                    'ec_halfwidth_ms_cm', 'ph_halfwidth', 'node_interval_dev_days',
                    'expansion_dev_days', 'internode_mm', 'leaf_axis_mm', 'leaflet_length_mm',
                    'leaflet_width_mm', 'truss_length_mm', 'flower_radius_mm']
        if any(getattr(self, name) <= 0 for name in positive):
            raise ValueError('Scales, durations and dimensions must be positive')
        for name in ['truss_after_node', 'truss_every_nodes', 'max_nodes']:
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= 100:
                raise ValueError(f'{name} must be an integer in 1..100')
        if self.truss_delay_dev_days < 0 or self.flower_delay_dev_days < 0:
            raise ValueError('Delays cannot be negative')


def demo_parameters() -> Parameters:
    """Arbitrary interface-testing values. NOT tomato production recommendations."""
    return Parameters('ILLUSTRATIVE_ONLY_v1', 10, 24, 18, 65, 65, 2, 3, 6, 4,
                      2, 4, 22, 65, 42, 22, 5, 137.5, 3, 2, 1, 3, 35, 5, 12)


def illustrative_response(env: Environment, parameters: Parameters) -> dict[str, float]:
    """Toy multiplicative development response; replace with a calibrated model.

    No carbon balance, respiration, reserves, nutrient uptake, CO2 or mortality.
    No light halts this toy model even though real plants can develop in darkness.
    """
    def tent(value: float, centre: float, width: float) -> float:
        return max(0.0, 1.0 - abs(value - centre) / width)

    p = parameters
    light_integral = env.ppfd_umol_m2_s * env.photoperiod_h * 3600 / 1e6
    return dict(light=min(1.0, light_integral / p.light_scale_mol_m2_day),
                temperature=tent(env.temperature_c, p.temperature_centre_c, p.temperature_halfwidth_c),
                humidity=tent(env.relative_humidity_pct, p.rh_centre_pct, p.rh_halfwidth_pct),
                solution_ec=tent(env.solution_ec_ms_cm, p.ec_centre_ms_cm, p.ec_halfwidth_ms_cm),
                solution_ph=tent(env.solution_ph, p.ph_centre, p.ph_halfwidth),
                water=1.0 if env.water_available else 0.0)


ResponseModel = Callable[[Environment, Parameters], dict[str, float]]


def organ_scene(dev_days: float, p: Parameters, plant_id: str) -> list[dict]:
    """Build one synthetic state. All geometry is in local plant XYZ millimetres."""
    organs: list[dict] = []

    def add(key: str, kind: str, parent: str | None, born: float,
            points: list | None = None, triangles: list | None = None) -> str:
        oid = f'{plant_id}/{key}'
        organs.append(dict(organ_id=oid, organ_type=kind, parent_id=parent,
                           birth_dev_days=born, age_dev_days=max(0, dev_days-born),
                           geometry_origin='procedural_demo', points_mm=points or [],
                           triangles_mm=triangles or []))
        return oid

    def expand(born: float) -> float:
        return min(1.0, max(0.0, (dev_days-born) / p.expansion_dev_days))

    root = add('plant', 'Plant', None, 0)
    stem = add('main_stem', 'MainStem', root, 0)
    count = min(p.max_nodes, int(dev_days / p.node_interval_dev_days))
    z = 0.0
    for index in range(1, count+1):
        born = index * p.node_interval_dev_days
        scale = expand(born)
        origin = np.array([0., 0., z])
        z += p.internode_mm * scale
        base = np.array([0., 0., z])
        add(f'internode_{index:03}', 'Internode', stem, born, [origin.tolist(), base.tolist()])
        angle = math.radians((index-1)*p.divergence_deg)
        direction = np.array([math.cos(angle), math.sin(angle), 0.25])
        direction /= np.linalg.norm(direction)
        side = np.array([-math.sin(angle), math.cos(angle), 0.])
        compound = add(f'L{index:03}', 'CompoundLeaf', stem, born)
        axis_end = base + direction*p.leaf_axis_mm*scale
        axis = add(f'L{index:03}/axis', 'SubStem', compound, born, [base.tolist(), axis_end.tolist()])
        # Five leaflets are a display topology only, not an inferred anatomical count.
        for k, (fraction, sign) in enumerate([(0.35,-1),(.35,1),(.7,-1),(.7,1),(1,0)], 1):
            attach = base + direction*p.leaf_axis_mm*scale*fraction
            vector = direction if sign == 0 else (direction*.35 + side*sign)
            vector /= np.linalg.norm(vector)
            lateral = np.cross(vector, [0.,0.,1.]); lateral /= np.linalg.norm(lateral)
            length = p.leaflet_length_mm*scale
            centre = attach + vector*length*.5 + np.array([0,0,p.leaflet_bow_mm*scale])
            tip = attach + vector*length
            left = attach + vector*length*.5 + lateral*p.leaflet_width_mm*scale*.5
            right = attach + vector*length*.5 - lateral*p.leaflet_width_mm*scale*.5
            rim = [attach,left,tip,right]
            triangles = [[centre.tolist(),rim[j].tolist(),rim[(j+1)%4].tolist()] for j in range(4)] if scale > 0 else []
            add(f'L{index:03}/F{k:02}', 'Leaflet', compound, born, triangles=triangles)
        if index >= p.truss_after_node and (index-p.truss_after_node) % p.truss_every_nodes == 0:
            truss_born = born+p.truss_delay_dev_days
            if dev_days >= truss_born:
                reach = p.truss_length_mm*expand(truss_born)
                end = base - direction*reach + np.array([0,0,reach*.2])
                truss = add(f'T{index:03}', 'Truss', stem, truss_born, [base.tolist(),end.tolist()])
                for flower in range(3):
                    flower_born = truss_born+p.flower_delay_dev_days+flower*p.node_interval_dev_days*.25
                    if dev_days < flower_born:
                        continue
                    c = end + side*(flower-1)*p.flower_radius_mm*3*expand(truss_born)
                    radius = p.flower_radius_mm*expand(flower_born)
                    rim = [c+np.array([math.cos(j*math.pi/5),math.sin(j*math.pi/5),0])*radius*(1 if j%2==0 else .45) for j in range(10)]
                    triangles = [[c.tolist(),rim[j].tolist(),rim[(j+1)%10].tolist()] for j in range(10)] if radius > 0 else []
                    add(f'T{index:03}/flower_{flower+1}', 'Flower', truss, flower_born, triangles=triangles)
    add('apex', 'GrowthShoot', stem, 0, [[0.,0.,z]])
    return organs


def simulate(environment_steps: list[Environment], parameters: Parameters, *, plant_id: str = 'demo_plant',
             response_model: ResponseModel = illustrative_response) -> dict:
    """Return initial state plus one state per environment interval; do not mutate inputs.

    Each callback returns named nonnegative factors in [0,1]; their product is
    development-days per calendar day. Nutrient concentrations reach the callback.
    This contract is deliberately replaceable and is not a calibrated growth law.
    """
    parameters.validate()
    if not isinstance(plant_id, str) or not plant_id or any(c in plant_id for c in '/\\<>'):
        raise ValueError('plant_id must be a nonempty local identifier')
    if not environment_steps or len(environment_steps) > 3660:
        raise ValueError('Supply 1..3660 sequential environment intervals')
    for env in environment_steps:
        env.validate()
    dev = elapsed = 0.0
    frames = [dict(day=0., development_days=0., environment=None, response_factors={},
                   organs=organ_scene(0.,parameters,plant_id))]
    for env in environment_steps:
        # Copy user mappings so a response implementation cannot mutate the supplied input.
        isolated = Environment(**json.loads(json.dumps(asdict(env))))
        factors = response_model(isolated, parameters)
        if not isinstance(factors,dict) or not factors:
            raise ValueError('Response model must return a nonempty factor mapping')
        for name, value in factors.items():
            if not isinstance(name, str):
                raise ValueError('Response names must be strings')
            finite(f'response.{name}', value, 0, 1)
        dev += env.dt_days * math.prod(factors.values())
        elapsed += env.dt_days
        frames.append(dict(day=elapsed, development_days=dev, environment=asdict(env),
                           response_factors=dict(factors), organs=organ_scene(dev,parameters,plant_id)))
    return dict(schema='procedural-growth-scaffold-1', plant_id=plant_id,
                parameters=asdict(parameters), response_model=getattr(response_model,'__name__','custom'),
                coordinate_frame='synthetic_local_plant_origin_z_up', units='mm',
                model_status='illustrative_not_calibrated', validated_growth=False,
                validated_metric=False, suitable_for_ppfd=False,
                limitations=['No measured plant reconstruction or photon transport.',
                             'No CO2, carbon balance, nutrient uptake, mortality or yield model.',
                             'EC/pH responses and developmental events are illustrative.',
                             'Nutrient concentrations are retained but unused by illustrative_response.',
                             'Five leaflets per compound and three flowers per truss are display topology.'],
                frames=frames)


def export_result(result: dict, out: Path, input_payload: dict) -> None:
    """Write a new directory only; OBJ geometry uses the shared mm->m conversion."""
    if out.resolve().is_relative_to(Path('build').resolve()) is False:
        raise ValueError('Generated output must be inside this project build directory')
    out.mkdir(parents=True, exist_ok=False)
    encode = lambda obj: json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)
    (out/'input.json').write_text(encode(input_payload),encoding='utf-8')
    (out/'simulation.json').write_text(encode(result),encoding='utf-8')
    fields = ['day','development_days','compound_leaf_count','leaflet_count','truss_count','flower_count','height_mm']
    with (out/'timeline.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for frame in result['frames']:
            organs=frame['organs'];types=[o['organ_type'] for o in organs]
            apex=next(o for o in organs if o['organ_type']=='GrowthShoot')
            writer.writerow(dict(day=frame['day'],development_days=frame['development_days'],
                compound_leaf_count=types.count('CompoundLeaf'),leaflet_count=types.count('Leaflet'),
                truss_count=types.count('Truss'),flower_count=types.count('Flower'),height_mm=apex['points_mm'][0][2]))
    lines=['# Synthetic display geometry ONLY. Units m; NOT PPFD ready.'];n=0
    for organ in result['frames'][-1]['organs']:
        lines.append('g '+organ['organ_id'].replace('/','_'))
        for triangle in organ['triangles_mm']:
            for point in mm_to_m(triangle):lines.append('v '+' '.join(format(float(v),'.12g') for v in point))
            lines.append(f'f {n+1} {n+2} {n+3}');n+=3
        if organ['points_mm']:
            for point in mm_to_m(organ['points_mm']):lines.append('v '+' '.join(format(float(v),'.12g') for v in point))
            ids=' '.join(str(n+i+1) for i in range(len(organ['points_mm'])))
            lines.append(('l ' if len(organ['points_mm'])>1 else 'p ')+ids);n+=len(organ['points_mm'])
    (out/'display_only_m.obj').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    template=Path(__file__).with_name('growth_simulator.html').read_text(encoding='utf-8')
    payload=json.dumps(result,ensure_ascii=True,allow_nan=False).replace('<','\\u003c')
    (out/'viewer.html').write_text(template.replace('__SIMULATION_JSON__',payload),encoding='utf-8')
    (out/'manifest.json').write_text(encode(dict(schema=result['schema'],model_status=result['model_status'],
        validated_growth=False,suitable_for_ppfd=False,groimp_import_verified=False,
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()})),encoding='utf-8')


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--demo',action='store_true');mode.add_argument('--input',type=Path)
    parser.add_argument('--out',required=True,type=Path);args=parser.parse_args(argv)
    try:
        if args.demo:
            payload=dict(plant_id='synthetic_demo',parameters=asdict(demo_parameters()),
                environment_steps=[asdict(Environment(1,250,16,24,65,2,6)) for _ in range(30)])
        else:
            payload=json.loads(args.input.read_text(encoding='utf-8'))
        result=simulate([Environment(**v) for v in payload['environment_steps']],Parameters(**payload['parameters']),plant_id=payload['plant_id'])
        export_result(result,args.out,payload)
    except (ValueError,TypeError,KeyError,OSError) as exc:
        parser.exit(2,f'Growth scaffold: {exc}\n')
    print(args.out.resolve()/'viewer.html');return 0


if __name__=='__main__':
    raise SystemExit(main())
