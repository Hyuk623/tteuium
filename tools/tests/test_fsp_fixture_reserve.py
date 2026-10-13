"""H5: explicit reserve assumptions without changing the default fixture."""
import uuid
import pytest
from tools.tomato_fsp_acceptance import scenario_fixture
from tools.vtc_growth_io import ROOT, ContractError, read_json

SOURCE = ROOT/'build/fsp_integration_20261011_p1_fixture_01'


def output():
    return ROOT/'build'/('h5_test_'+uuid.uuid4().hex)


@pytest.mark.parametrize('value', [-1, float('nan'), float('inf'), True, '0.1'])
def test_invalid_reserve_creates_no_output(value):
    out=output()
    with pytest.raises(ContractError):
        scenario_fixture(SOURCE,out,plant_reserve_gC=value,reserve_source_kind='fixture_declared',reserve_source_ref='test')
    assert not out.exists()


@pytest.mark.parametrize('kwargs', [
    dict(plant_reserve_gC=.1),
    dict(plant_reserve_gC=.1,reserve_source_kind='measured',reserve_source_ref='test'),
    dict(plant_reserve_gC=.1,reserve_source_kind='fixture_declared',reserve_source_ref=' '),
    dict(reserve_source_kind='fixture_declared'),
])
def test_missing_or_inappropriate_provenance(kwargs):
    out=output()
    with pytest.raises(ContractError):
        scenario_fixture(SOURCE,out,**kwargs)
    assert not out.exists()


@pytest.mark.parametrize('value',[0.,.1])
def test_only_declared_reserve_and_its_provenance_change(value):
    if not SOURCE.exists():
        pytest.skip('producer fixture not installed')
    default=read_json(scenario_fixture(SOURCE,output()))
    changed=read_json(scenario_fixture(SOURCE,output(),plant_reserve_gC=value,
                      reserve_source_kind='fixture_declared',reserve_source_ref='H5 test'))
    assert default['fixture'] is True
    for pid,plant in changed['plant_initialization'].items():
        assert plant['reserve_gC']==value
        assert plant.pop('reserve_source_kind')=='fixture_declared'
        assert plant.pop('reserve_source_ref')=='H5 test'
        assert plant.pop('reserve_unit')=='gC'
        assert default['plant_initialization'][pid]['reserve_gC']==.2
        plant['reserve_gC']=.2
    assert changed==default
