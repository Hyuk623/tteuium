"""Audit visible compound axes and candidate blade ratios; do not impute anatomy.

python -m tools.f2_compound_measurements --out build/compound_structure_f2_f7_20261006_01
"""
from __future__ import annotations
import argparse
import csv
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from tools.f2_f7_analysis import read_json, save_json, table, sha


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def ratio_interval(a: float, b: float, endpoint_error_px: float) -> tuple[float,float]:
    if b <= 2*endpoint_error_px:
        raise ValueError('denominator unresolved')
    return max(0., a-2*endpoint_error_px)/(b+2*endpoint_error_px), (a+2*endpoint_error_px)/(b-2*endpoint_error_px)


def run(out: Path) -> dict:
    out=out.resolve()
    if 'build' not in out.parts: raise ValueError('build output required')
    sources=read_json(out/'crop_sources.json')
    annotations=read_csv(out/'compound_annotations.csv')
    candidates=read_csv(out/'candidate_annotations.csv')
    hashes={}
    for p in [out/'crop_sources.json',out/'compound_annotations.csv',out/'candidate_annotations.csv']:
        hashes[str(p)]=sha(p)
    for s in sources:
        p=Path(s['source']); hashes[str(p)]=sha(p)
    measured=[]
    compound_rows=[]
    cards=[]
    for a in annotations:
        path=out/a['crop_file']
        hashes[str(path)]=sha(path)
        im=Image.open(path).convert('RGB')
        draw=ImageDraw.Draw(im)
        axis=np.array([[float(v) for v in pair.split()] for pair in a['visible_axis_xy_px'].split(';')])
        length=float(np.linalg.norm(np.diff(axis,axis=0),axis=1).sum())
        draw.line([tuple(p) for p in axis],fill='#00deff',width=4)
        for i,p in enumerate(axis):
            x,y=p; draw.ellipse((x-4,y-4,x+4,y+4),fill='#00deff')
            draw.text((x+5,y-14),f'R{i}',fill='#003344')
        local=[r for r in candidates if r['photo']==a['photo']]
        for c in local:
            points=[(float(c[f'{part}_x_px']),float(c[f'{part}_y_px'])) for part in ('blade_base','blade_tip','adjacent_main_base','adjacent_main_tip')]
            lb=float(np.linalg.norm(np.array(points[1])-points[0]))
            lm=float(np.linalg.norm(np.array(points[3])-points[2]))
            lo,hi=ratio_interval(lb,lm,5.)
            measured.append(dict(photo=a['photo'],candidate_id=c['candidate_id'],
                projected_blade_length_px=lb,projected_adjacent_main_length_px=lm,
                projected_length_ratio=lb/lm,ratio_lower_endpoint5px=lo,ratio_upper_endpoint5px=hi,
                rachis_fraction_from_anatomical_base='NaN',attachment_status=c['attachment_status'],
                class_status=c['class_status'],source_kind='measured_small_n',n_photos=1,n_blades=1,
                independent_compound_id='unavailable',projection='unpressed_folded_photo',
                outline_metrics_status='unavailable_no_isolated_boundary',generator_parameter_eligible=False,
                quality_flags=c['quality_flags']))
            draw.line(points[:2],fill='#ff00c8',width=4)
            draw.line(points[2:],fill='#ff9b00',width=3)
            draw.text(points[1],c['candidate_id'],fill='#cc0088')
        compound_rows.append(dict(photo=a['photo'],n_candidate_interjected_blades=len(local),
            main_pairs_confirmed='NaN',terminal_present=a['terminal_present'],
            interjected_count_confirmed='NaN',full_rachis_length_px='NaN',
            traced_visible_axis_length_px=length,full_axis_available=False,
            anatomical_base_confirmed=a['anatomical_base_confirmed'],
            terminal_attachment_confirmed=a['terminal_attachment_confirmed'],
            main_count_user_given=a['main_count_user_given'],interjected_count_user_given=a['interjected_count_user_given'],
            count_basis='main_and_interjected_separate;user_given_counts_not_measured',
            source_kind='measured_small_n',n_photos=1,n_independent_compounds='unavailable',
            identity_group=a['identity_group'],quality_flags=a['quality_flags']))
        im.save(out/f"{a['photo']}_labelled_rachis.png")
        card=Image.new('RGB',(480,580),'white')
        card.paste(ImageOps.contain(im,(470,480)),(5,90))
        d=ImageDraw.Draw(card)
        d.text((7,6),f"{a['photo']} | {len(local)} candidate blades",fill='black')
        d.text((7,25),'Cyan: visible axis only; full rachis unavailable',fill='#007080')
        d.text((7,44),'Magenta: candidate; orange: provisional adjacent main',fill='#a00070')
        d.text((7,63),'No imputed attachment fraction or anatomical count',fill='black')
        cards.append(card)
    table(out/'compound_measurements.csv',compound_rows)
    table(out/'interjected_leaflets.csv',measured)
    sheet=Image.new('RGB',(1920,1160),'white')
    for i,card in enumerate(cards): sheet.paste(card,((i%4)*480,(i//4)*580))
    sheet.save(out/'labelled_rachises.png')
    vals=[r['projected_length_ratio'] for r in measured]
    summary=dict(n_original_compound_photos=7,n_additional_user_compound_photos=1,n_photos_reviewed=8,
        n_candidate_blades=len(measured),n_photos_with_candidate_ratios=len({r['photo'] for r in measured}),
        n_independent_compounds=None,possible_repeat_groups=['leaf_03/leaf_04','leaf_24/leaf_25'],
        confirmed_rachis_fractions=0,confirmed_total_main_counts=0,confirmed_total_interjected_counts=0,
        descriptive_candidate_ratio_range=dict(min=min(vals),max=max(vals),source_kind='measured_small_n',
            n_candidate_blades=len(vals),n_photos=len({r['photo'] for r in measured}),n_independent_compounds=None,
            interpretation='projected endpoint chords;candidate identity and adjacency provisional;not anatomical length ratios;not a generator prior'),
        main_leaflets_user_general='5-7 main only; additional interjected count separate (F.12)',
        absolute_scale_status='not_estimated',f2_status='photo_audit_and_provisional_projected_ratios_complete;anatomical_parameters_unavailable',
        required_evidence=['Unique compound IDs to identify repeat photographs',
                           'Spread attached compound with base and terminal attachment visible',
                           'Label each main and interjected attachment on both sides',
                           'Separate intact flat blades from multiple independent compounds for class validation',
                           'No ruler lines across blades; ruler optional for ratios'],
        f3_authorized=False)
    save_json(out/'F2_summary.json',summary)
    save_json(out/'F2_input_provenance.json',dict(sha256_before=hashes,all_unchanged=all(sha(Path(p))==h for p,h in hashes.items())))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True,type=Path)
    print(run(p.parse_args().out))
