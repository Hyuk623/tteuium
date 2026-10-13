from tools.density_flowering_report import build
from tools.first_flowering import templates, analyse
from tools.leaf_light.common import write_json,write_rows,rows


def test_join_does_not_create_flowering_or_density_optimum(tmp_path):
    light=tmp_path/'light';light.mkdir()
    cols=('case_id','density_id','snapshot_date','plants_per_m2','lower_incident_both_faces_umol_m2_s',
          'upper_incident_both_faces_umol_m2_s','plant_mean_cv')
    write_rows(light/'density_comparison.csv',[dict(zip(cols,['c','d','2026-09-30',4,20,100,.2]))],cols)
    write_json(light/'results.json',{'ppfd_validation':{'status':'unavailable'}})
    templates(tmp_path/'records')
    analyse(tmp_path/'records',tmp_path/'flowering',tmp_path/'records/analysis_settings.json')
    result=build(light,tmp_path/'flowering',tmp_path/'joined')
    assert result['candidate_selection']=='unavailable_pending_validation'
    table=rows(tmp_path/'joined/density_flowering_comparison.csv')
    assert table[0]['optimum']=='unavailable'
    assert table[0]['n_independent_flowering_plots']=='unavailable'
