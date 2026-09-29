"""Portable snapshots must execute away from their original paths and reject changed returns."""
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import nbformat
import pytest

from tools.colab_xl_bridge import archive_files, import_result, pack, sha, verified_archive, zip_write
from tools.leaf_light import common
from tools.tests.test_groimp_structure_export import fixture_snapshot


def extract(bundle, target):
    _,files=verified_archive(bundle,'bundle.json')
    for name,data in files.items():
        p=target/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)


def execute(target):
    env=dict(os.environ);env.pop('PYTHONPATH',None)
    result=subprocess.run([sys.executable,'-X','utf8','-m','tools.colab_xl_bridge','run','--root',str(target)],
        cwd=target,env=env,capture_output=True,text=True,encoding='utf-8',timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    return Path(result.stdout.strip().splitlines()[-1])


def test_isolated_roundtrip_resume_and_notebook(tmp_path,monkeypatch):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    run=fixture_snapshot(tmp_path/'original')
    pack(run,tmp_path/'package')
    notebook=nbformat.read(tmp_path/'package/Tomato_XL_Colab.ipynb',as_version=4)
    nbformat.validate(notebook)
    for cell in notebook.cells:
        if cell.cell_type=='code':
            compile(cell.source,'notebook','exec')
    bundle=tmp_path/'package/tomato_colab_inputs.zip'
    target=tmp_path/'linux_style_location'
    extract(bundle,target)
    # Original hierarchy is inaccessible: only the portable source copies are used.
    original=tmp_path/'original/backup.json'; before=original.read_bytes(); original.rename(original.with_suffix('.retained'))
    result=execute(target)
    second=execute(target)
    receipt=import_result(bundle,result,tmp_path/'accepted')
    assert receipt['status']=='import_verified'
    assert original.with_suffix('.retained').read_bytes()==before
    assert archive_files(result)['DT-001/Model.rgg']==archive_files(second)['DT-001/Model.rgg']
    m,files=verified_archive(result,'result.json')
    files['DT-001/coordinates.csv']+=b'changed\n'
    # Even a recomputed transport hash cannot hide changed scientific artifacts.
    m['files']['DT-001/coordinates.csv']=sha(files['DT-001/coordinates.csv'])
    files['result.json']=json.dumps(m).encode()
    bad=tmp_path/'tampered.zip';zip_write(bad,files)
    with pytest.raises(ValueError,match='artifact differs'):
        import_result(bundle,bad,tmp_path/'rejected')
    assert not (tmp_path/'rejected').exists()


@pytest.mark.parametrize('name',['../outside','/absolute','C:/path','a\\b'])
def test_unsafe_archive_paths(tmp_path,name):
    p=tmp_path/'bad.zip'
    with zipfile.ZipFile(p,'w') as z:
        entry=zipfile.ZipInfo();entry.filename=name;z.writestr(entry,b'x')
    with pytest.raises(ValueError,match='Unsafe'):
        archive_files(p)


def test_modified_input_blocks_pack(tmp_path,monkeypatch):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    run=fixture_snapshot(tmp_path/'source')
    (tmp_path/'source/backup.json').write_text('{}')
    with pytest.raises(ValueError,match='backup changed'):
        pack(run,tmp_path/'package')
    assert not (tmp_path/'package').exists()
