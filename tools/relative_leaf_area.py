"""Normalize labelled leaf areas to the first supplied leaf, preserving source areas and geometry.

python -m tools.relative_leaf_area --areas build/leaf_areas.csv --out build/fresh_ratios
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from tools.leaf_light.common import StudyError, file_hash, number, output_dir, rows, write_json, write_rows

GROUP = ('plant_id', 'session_id', 'capture_date', 'area_method', 'area_scope', 'view_id')
COLUMNS = (*GROUP, 'label_id', 'area_cm2')
OUTPUT = (*COLUMNS, 'reference_label_id', 'reference_area_cm2', 'relative_area', 'ratio_status')
SCOPES = ('measured_leaf_area', 'projected_mask_area', 'supported_partial_surface')
PIXEL_SCOPES = ('detected_visible_mask', 'detected_bbox')


def normalize(records: list[dict], *, area_column: str = 'area_cm2') -> list[dict]:
    """First row per comparable group is the reference; never skip an invalid first leaf."""
    if area_column not in ('area_cm2', 'area_px2'):
        raise StudyError('Unsupported area column')
    columns = (*GROUP, 'label_id', area_column)
    scopes = PIXEL_SCOPES if area_column == 'area_px2' else SCOPES
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for source in records:
        r = {k: source.get(k) for k in columns}
        for k in ('plant_id','session_id','area_method','area_scope','label_id'):
            if not isinstance(r[k], str) or not r[k] or r[k]=='unavailable':
                raise StudyError(f'Explicit {k} required')
        for k in ('capture_date','view_id'):
            r[k] = r[k] if r[k] not in ('unavailable','') else None
        if r['area_scope'] not in scopes:
            raise StudyError('Unknown area scope')
        if (r['area_scope']=='projected_mask_area' or area_column=='area_px2') and not r['view_id']:
            raise StudyError('Projected mask ratios require the same explicit view_id')
        r[area_column] = number(r[area_column],area_column,missing=True)
        if r[area_column] is not None and r[area_column] < 0:
            raise StudyError('Negative leaf area')
        groups[tuple(r[k] for k in GROUP)].append(r)
    result=[]
    for rr in groups.values():
        if len({r['label_id'] for r in rr}) != len(rr):
            raise StudyError('Duplicate label in one area group; aggregate reviewed patches first')
        reference=rr[0]
        baseline=reference[area_column]
        for r in rr:
            status=('reference_unavailable' if baseline is None else
                    'reference_zero' if baseline==0 else
                    'area_unavailable' if r[area_column] is None else 'computed')
            result.append(dict(r,reference_label_id=reference['label_id'],**{'reference_'+area_column:baseline},
                               relative_area=r[area_column]/baseline if status=='computed' else None,
                               ratio_status=status))
    return result


def run(path: Path, out: Path) -> dict:
    before=file_hash(path)
    result=normalize(rows(path,COLUMNS))
    if file_hash(path)!=before:
        raise StudyError('Source areas changed during normalization')
    folder=output_dir(out)
    write_rows(folder/'relative_leaf_areas.csv',result,OUTPUT)
    report=dict(schema='relative-leaf-area-1',source=str(path.resolve()),source_sha256=before,
                reference_rule='first supplied label in each plant/session/date/method/scope/view group',
                formula='relative_area = area_cm2 / reference_area_cm2',units='dimensionless',
                rows=result,physical_validation=False,
                limitation='Normalization preserves source area and coverage limitations; it does not reconstruct missing tissue.')
    write_json(folder/'audit.json',report)
    return report


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--areas',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();report=run(args.areas,args.out)
    print(dict(rows=len(report['rows']),units='dimensionless'))


if __name__=='__main__':
    main()
