"""Join density light comparisons to independent plot flowering summaries.

No optimal density is manufactured from missing measurements, unequal follow-up,
or a point-light demonstration. python -m tools.density_flowering_report --help
"""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

from tools.leaf_light.common import (StudyError,file_hash,output_dir,read_json,rows,write_json,write_rows)


def build(light_dir: Path, flowering_dir: Path, out: Path) -> dict:
    light=rows(light_dir/'density_comparison.csv')
    flower=rows(flowering_dir/'density_flowering.csv')
    density={r['density_id']:r for r in flower}
    if len(density)!=len(flower):
        raise StudyError('Duplicate density summary')
    summary=[]
    for l in light:
        f=density.get(l['density_id'],{})
        summary.append(dict(case_id=l['case_id'],density_id=l['density_id'],snapshot_date=l['snapshot_date'],
            plants_per_m2=l['plants_per_m2'],
            lower_incident_both_faces_umol_m2_s=l['lower_incident_both_faces_umol_m2_s'],
            upper_incident_both_faces_umol_m2_s=l['upper_incident_both_faces_umol_m2_s'],
            plant_mean_cv=l['plant_mean_cv'],
            n_independent_flowering_plots=f.get('n_independent_plots'),
            plot_mean_observed_open_fraction=f.get('mean_plot_observed_open_fraction'),
            candidate_status='awaiting_independent_validation_and_followup_review',
            optimum=None))
    # Keep observed densities even when no eligible geometry job exists.
    for did in sorted(set(density)-{l['density_id'] for l in light}):
        f=density[did]
        summary.append(dict(case_id=None,density_id=did,snapshot_date=None,plants_per_m2=None,
            lower_incident_both_faces_umol_m2_s=None,upper_incident_both_faces_umol_m2_s=None,plant_mean_cv=None,
            n_independent_flowering_plots=f['n_independent_plots'],plot_mean_observed_open_fraction=f['mean_plot_observed_open_fraction'],
            candidate_status='light_unavailable',optimum=None))
    folder=output_dir(out)
    columns=('case_id','density_id','snapshot_date','plants_per_m2','lower_incident_both_faces_umol_m2_s',
        'upper_incident_both_faces_umol_m2_s','plant_mean_cv','n_independent_flowering_plots',
        'plot_mean_observed_open_fraction','candidate_status','optimum')
    write_rows(folder/'density_flowering_comparison.csv',summary,columns)
    table='<table border="1"><tr>'+''.join(f'<th>{escape(c)}</th>' for c in columns)+'</tr>'
    for row in summary:
        table+='<tr>'+''.join(f'<td>{escape(str(row[c] if row[c] is not None else "unavailable"))}</td>' for c in columns)+'</tr>'
    (folder/'comparison.html').write_text('<!doctype html><meta charset="utf-8"><title>Density and first flowering</title>'
        '<h1>Light distribution and first flowering</h1><p>Compare only tested conditions. '
        'Observed open fractions are not censor-adjusted probabilities; check follow-up intervals and plot replication. '
        'The leaf light columns include both faces and are separate from front-face sensor PPFD. '
        'No yield, profit or optimal density is inferred.</p>'+table+'</table>',encoding='utf-8')
    sources=[light_dir/'density_comparison.csv',light_dir/'results.json',flowering_dir/'density_flowering.csv',flowering_dir/'analysis.json']
    result=dict(status='comparison_ready_for_review',primary_endpoint='first_open_flower',co2_recorded=False,
        candidate_selection='unavailable_pending_validation',
        light_validation=read_json(light_dir/'results.json')['ppfd_validation'],
        flowering_prediction=read_json(flowering_dir/'analysis.json')['prediction_status'],
        source_hashes={str(p.resolve()):file_hash(p) for p in sources})
    write_json(folder/'comparison.json',result)
    return result


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--light',type=Path,required=True)
    p.add_argument('--flowering',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();print(build(args.light,args.flowering,args.out))


if __name__=='__main__':
    main()
