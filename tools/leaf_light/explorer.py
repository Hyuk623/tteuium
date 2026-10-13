"""Offline inspector joining photographs, subset meshes and measured PPFD."""
from __future__ import annotations

import html
import json
import os
from pathlib import Path
from urllib.parse import quote

from .common import read_json


def make_explorer(folder: Path, summary: dict, records: list[dict], run_paths: list[Path]) -> None:
    def relative(path: Path) -> str:
        return quote(Path(os.path.relpath(path, folder)).as_posix(), safe="/")

    sessions = []
    for path in run_paths:
        run = read_json(path)
        if run["plant_id"] not in summary["protocol"]["evaluation_plants"]:
            continue
        recon_path = Path(run["input_paths"]["reconstruction"])
        recon = read_json(recon_path)
        capture = read_json(Path(recon["capture_path"]))
        frames = {f["image_file"]: f for f in capture["frames"]}
        options = []
        for variant in recon["variants"]:
            photos = []
            for name in variant["image_files"]:
                frame = frames[name]
                if frame.get("image_path") and Path(frame["image_path"]).is_file():
                    photos.append(dict(name=name, url=relative(Path(frame["image_path"]))))
            options.append(dict(id=variant["variant_id"], photos=photos,
                                mesh=relative(recon_path.parent / variant["geometry_file"]),
                                status=variant["status"], failed_leaves=variant.get("n_failed_leaves", "unavailable")))
        sessions.append(dict(id=run["session_id"], slot=run["session_slot"], plant=run["plant_id"],
                             variants=options, blockers=run["blockers"],
                             assumptions=run.get("non_observed_inputs", []), source=relative(path)))
    payload = json.dumps(dict(sessions=sessions, records=records), ensure_ascii=False).replace("<", "\\u003c")
    banner = ("SYNTHETIC DEMONSTRATION: no real plant photographs or measurements"
              if summary["data_kind"] == "synthetic" else
              "No evaluation data loaded" if summary["data_kind"] == "no_data" else
              "Observed data: consult the evaluation report before drawing conclusions")
    page = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Leaf light result inspector</title><style>body{font:16px system-ui;background:#f6faf7;color:#173b2a;max-width:1100px;margin:30px auto;padding:0 16px}select{padding:8px;margin:8px}td,th{padding:8px;border:1px solid #bdcfc4;text-align:left}table{border-collapse:collapse;font-size:14px;width:100%}.scroll{overflow:auto}.notice{padding:16px;background:#fff1cc}.photos{display:flex;gap:12px;overflow:auto}.photos img{max-height:200px;max-width:280px;object-fit:contain}a{color:#126846}pre{white-space:pre-wrap}</style>
<h1>Photographs → leaf geometry → measured light</h1><p class="notice">BANNER</p>
<p><a href="report.html">Open accuracy and view-count report</a></p>
<label>Session <select id="session"></select></label><label>Photograph subset <select id="variant"></select></label>
<p id="state"></p><p><a id="mesh">Open selected leaf triangles (CSV)</a> · <a id="source">Inspect run provenance</a></p>
<details><summary>Selected photographs</summary><div class="photos" id="photos"></div></details>
<details><summary>Unmeasured or assumed inputs</summary><pre id="assumptions"></pre></details>
<h2>Sensor comparison</h2><p>PPFD in µmol m⁻² s⁻¹. Empty field excludes plant surfaces. Unavailable is never zero.</p>
<div class="scroll"><table><thead><tr><th>Site</th><th>Repeat</th><th>Height region</th><th>Measured</th><th>Predicted</th><th>Empty field</th><th>Prediction − measurement</th><th>Status</th></tr></thead><tbody id="readings"></tbody></table></div>
<p>This viewer displays saved calculations. It does not estimate photosynthesis, change the LED model or fit evaluation measurements.</p>
<script type="application/json" id="data">PAYLOAD</script><script>
const data=JSON.parse(document.getElementById('data').textContent);
const $=id=>document.getElementById(id);
const option=(label,value)=>{const o=document.createElement('option');o.textContent=label;o.value=value;return o;};
data.sessions.forEach((s,i)=>$('session').append(option(s.plant+' / '+s.slot+' / '+s.id,i)));
function sessionChanged(){const s=data.sessions[$('session').value];$('variant').replaceChildren();if(!s){$('state').textContent='No evaluation sessions available.';return;}s.variants.forEach(v=>$('variant').append(option(v.id,v.id)));draw();}
function draw(){const s=data.sessions[$('session').value];if(!s)return;const v=s.variants.find(v=>v.id===$('variant').value);
$('state').textContent='Geometry: '+v.status+'; failed annotated leaflets: '+v.failed_leaves+'. '+(s.blockers.length?'Blocked: '+s.blockers.join(', '):'No run-level blockers recorded.');
$('mesh').href=v.mesh;$('source').href=s.source;$('assumptions').textContent=s.assumptions.join('\n')||'No non-observed inputs listed.';
$('photos').replaceChildren();v.photos.forEach(p=>{const a=document.createElement('a');a.href=p.url;const img=document.createElement('img');img.src=p.url;img.alt=p.name;img.loading='lazy';a.append(img);$('photos').append(a);});
if(!v.photos.length)$('photos').textContent='No source photographs available for this demonstration.';
$('readings').replaceChildren();data.records.filter(r=>r.plant_id===s.plant&&r.session_id===s.id&&r.variant_id===v.id).forEach(r=>{
const real=r.measured_ppfd_umol_m2_s,pred=r.predicted_ppfd_umol_m2_s;const difference=(real!==''&&pred!==''&&Number.isFinite(Number(real))&&Number.isFinite(Number(pred)))?(Number(pred)-Number(real)).toFixed(2):'unavailable';
const tr=document.createElement('tr');[r.site_id,r.replicate_id,r.region_label,real,pred,r.no_plants_ppfd_umol_m2_s,difference,r.measurement_status+' / '+r.run_status].forEach(x=>{const td=document.createElement('td');td.textContent=x;tr.append(td);});$('readings').append(tr);});}
$('session').addEventListener('change',sessionChanged);$('variant').addEventListener('change',draw);sessionChanged();
</script></html>'''
    page = page.replace("BANNER", html.escape(banner)).replace("PAYLOAD", payload)
    (folder / "inspector.html").write_text(page, encoding="utf-8")
