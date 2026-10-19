"""Register existing result images/viewer exports. Does not run the research engine."""
import argparse
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from product.backend.db import connect, initialize

INPUT_KINDS = ('observed_geometry', 'synthetic_fixture', 'assumed')
MAX_BYTES = 20 * 1024 * 1024


def register_result(db_path: Path, source: Path, *, plant_id: str, title: str,
                    run_id: str, scenario_id: str, generated_at: datetime, input_kind: str) -> str:
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError('generated_at requires a timezone')
    if input_kind not in INPUT_KINDS:
        raise ValueError('unknown input kind')
    if any(not value.strip() or len(value)>200 for value in (plant_id,title,run_id,scenario_id)):
        raise ValueError('metadata must be nonempty, at most 200 characters')
    if source.stat().st_size > MAX_BYTES:
        raise ValueError('export exceeds 20 MiB')
    raw=source.read_bytes()
    suffix=source.suffix.lower()
    if suffix=='.png' and raw.startswith(b'\x89PNG\r\n\x1a\n'):
        kind='image'
    elif suffix in ('.jpg','.jpeg') and raw.startswith(b'\xff\xd8\xff'):
        kind='image'
    elif suffix=='.html':
        content=raw.decode('utf-8-sig')
        if '__DATA__' in content or '<script' not in content.lower():
            raise ValueError('import a generated self-contained viewer, not the template')
        kind='viewer'
    else:
        raise ValueError('supported exports: PNG, JPEG, generated HTML viewer')
    digest=hashlib.sha256(raw).hexdigest()
    initialize(db_path)
    identifier=uuid.uuid4().hex
    directory=db_path.parent/'simulation-assets'
    directory.mkdir(parents=True,exist_ok=True)
    asset=directory/(identifier+suffix)
    with connect(db_path) as db:
        if not db.execute('SELECT 1 FROM plants WHERE id=?',(plant_id,)).fetchone():
            raise ValueError('register the plant first; matching must be explicit')
        old=db.execute('SELECT id FROM simulation_results WHERE plant_id=? AND run_id=? AND scenario_id=? AND sha256=?',(plant_id,run_id,scenario_id,digest)).fetchone()
        if old:
            return old['id']
        asset.write_bytes(raw)
        try:
            db.execute('INSERT INTO simulation_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                (identifier,plant_id,title,run_id,scenario_id,generated_at.astimezone(timezone.utc).isoformat(),input_kind,source.name,digest,asset.name,kind,datetime.now(timezone.utc).isoformat()))
        except Exception:
            asset.unlink(missing_ok=True)
            raise
    return identifier


def list_results(db_path: Path, plant_id: str) -> list[dict]:
    with connect(db_path) as db:
        result=[]
        for row in db.execute('SELECT * FROM simulation_results WHERE plant_id=? ORDER BY generated_at DESC',(plant_id,)):
            item=dict(row)
            item.pop('asset_name')
            item['asset_url']='/api/simulations/'+item['id']+'/asset'
            item['provenance']='model'
            result.append(item)
        return result


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,default=Path('build/product/product.sqlite3'))
    parser.add_argument('--file',type=Path,required=True)
    for flag in ('plant-id','title','run-id','scenario-id','generated-at'):
        parser.add_argument('--'+flag,required=True)
    parser.add_argument('--input-kind',choices=INPUT_KINDS,required=True)
    args=parser.parse_args()
    identifier=register_result(args.db,args.file,plant_id=args.plant_id,title=args.title,run_id=args.run_id,scenario_id=args.scenario_id,generated_at=datetime.fromisoformat(args.generated_at),input_kind=args.input_kind)
    print('Registered simulation result: '+identifier)


if __name__=='__main__':
    main()
