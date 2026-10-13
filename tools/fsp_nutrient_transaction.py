"""Science-gated transaction mechanics fixture; NOT connected nutrient-constrained growth."""
from __future__ import annotations
import argparse
import re
from pathlib import Path
from tools.vtc_growth_io import require,read_json,write_json,digest,aware,number,fresh_build


def begin(folder: Path,proposal: dict) -> str:
    require(proposal.get('schema_version')=='fsp-resource-protocol-fixture-1','unsupported transaction schema')
    require(proposal.get('fixture') is True,'no approved biological/native handshake contract')
    require(aware(proposal['interval_end'])>aware(proposal['interval_start']),'invalid interval')
    require(all(isinstance(proposal[k],str) and re.fullmatch('[0-9a-f]{64}',proposal[k]) for k in ('predecessor_sha256','model_sha256','parameter_sha256')),'binding hashes required')
    require(proposal['plants'],'plant membership empty')
    for plant in proposal['plants'].values():
        require(set(plant)=={'carbon_gC','water_ml','elements_mg'},'explicit resource units required')
        number(plant['carbon_gC'],'carbon_gC',0);number(plant['water_ml'],'water_ml',0)
        require(plant['elements_mg'],'element identities required')
        for value in plant['elements_mg'].values():number(value,'element mg',0)
    tx=digest(proposal)
    if folder.exists():require(read_json(folder/'proposal.json')==proposal,'conflicting transaction retry');return tx
    folder=fresh_build(folder);write_json(folder/'proposal.json',proposal);return tx


def finalize(folder: Path,response: dict,actual: dict,now: str) -> dict:
    """Only a declared fixture chooses actual resources; no uptake/allocation law here."""
    proposal=read_json(folder/'proposal.json');tx=digest(proposal);target=folder/'committed'
    binding={k:proposal[k] for k in ('predecessor_sha256','model_sha256','parameter_sha256','interval_start','interval_end')}
    require(response.get('transaction_id')==tx and actual.get('transaction_id')==tx,'wrong/stale transaction')
    require(response.get('binding')==binding and actual.get('binding')==binding,'stale model/interval/predecessor')
    request_hash=digest(dict(response=response,actual=actual))
    if target.exists():
        done=read_json(target/'commit.json');require(done['request_sha256']==request_hash,'conflicting finalize retry');return done
    require(aware(now)<=aware(response['expires_at']),'availability response timed out')
    require(set(response['available'])==set(actual['used'])==set(proposal['plants']),'cross-plant or missing resource response')
    balance={}
    for pid,demand in proposal['plants'].items():
        available=response['available'][pid];used=actual['used'][pid]
        require(set(available)==set(used)==set(demand),'resource category mismatch')
        require(set(available['elements_mg'])==set(used['elements_mg'])==set(demand['elements_mg']),'element coverage mismatch')
        returned={'elements_mg':{}}
        for category in ('carbon_gC','water_ml'):
            limit=number(available[category],category,0);amount=number(used[category],category,0)
            require(amount<=min(limit,demand[category]),'actual use exceeds demand/availability');returned[category]=limit-amount
        for element,limit in available['elements_mg'].items():
            number(limit,'available element',0);amount=number(used['elements_mg'][element],'used element',0)
            require(amount<=min(limit,demand['elements_mg'][element]),'element use exceeds demand/availability');returned['elements_mg'][element]=limit-amount
        balance[pid]=dict(available=available,used=used,returned_unused=returned)
    temporary=folder/'.commit_partial';require(not temporary.exists(),'incomplete publication: inspect partial before retry');temporary.mkdir()
    done=dict(status='protocol_fixture_committed',native_handshake=False,biological_coupling='unavailable_missing_science_contract',transaction_id=tx,request_sha256=request_hash,balances=balance)
    write_json(temporary/'commit.json',done);temporary.rename(target);return done


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--proposal',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(begin(a.out,read_json(a.proposal)))


if __name__=='__main__':main()
