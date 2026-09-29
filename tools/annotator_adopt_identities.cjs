// Applies reviewed cross-view identities with the editor's own adopt/status functions.
// stdin: {backup, frames:[{key,image_file,width,height}], groups:[{group_id, provenance, observations:[{key, source_annotation_id}]}]}
// stdout: {backup, applied:[{group_id, leaf_key, views}], skipped:[{group_id, key, source_annotation_id, reason}]}
// Visibility is set only from explicit human answers passed in job.visibility.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');

const job = JSON.parse(fs.readFileSync(0, 'utf8'));
const html = fs.readFileSync(path.join(__dirname, 'leaf_point_annotator.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const nodes = new Map();
const context = vm.createContext({crypto, console: {log() {}, warn() {}, error: console.error},
  setTimeout: () => 0, clearTimeout: () => {}, IntersectionObserver: class { disconnect() {} observe() {} },
  localStorage: {getItem: () => null, setItem: () => {}},
  document: {getElementById: id => { if (!nodes.has(id)) nodes.set(id, {value: '2', checked: true, hidden: false, textContent: ''}); return nodes.get(id); }},
  window: {devicePixelRatio: 1}});
vm.runInContext(script.slice(0, script.indexOf('// Wiring')) + `
  updateSide = () => {}; refreshSelects = () => {}; draw = () => {};
  this.api = {ui, store, images, vstate, adoptLeafletDetection, setLeafViewStatus};
})();`, context);
const a = context.api;
const backup = job.backup;
a.ui.plant = backup.plant_id;
a.ui.variant = '__all__';
a.store.variants = JSON.parse(JSON.stringify(backup.variants));
for (const f of job.frames) a.images.set(f.key, {key: f.key, name: f.image_file, size: [f.width, f.height]});

const detectionFor = (key, sourceId) => (a.vstate().membership?.detections?.[key] || [])
  .filter(d => d.class_name === 'leaflet' && String(d.source?.source_annotation_id) === String(sourceId));
const applied = [], skipped = [];
for (const group of job.groups) {
  let leafKey = null;
  const views = [];
  for (const obs of group.observations) {
    const found = detectionFor(obs.key, obs.source_annotation_id);
    const skip = reason => skipped.push({group_id: group.group_id, key: obs.key, source_annotation_id: obs.source_annotation_id, reason});
    if (found.length !== 1) { skip(found.length ? 'ambiguous_detection' : 'detection_not_found'); continue; }
    const det = found[0];
    if (det.adopted_into && det.adopted_into.leaf_key !== leafKey) { skip('already_adopted_elsewhere'); continue; }
    if (leafKey && a.vstate().leaflets[leafKey]?.bboxes?.[obs.key]) { skip('leaf_already_has_box_in_view'); continue; }
    leafKey = a.adoptLeafletDetection(obs.key, det.annotation_id, leafKey);
    a.setLeafViewStatus(leafKey, obs.key, 'identity_review', 'confirmed');
    views.push(obs.key);
  }
  if (leafKey) {
    // Provenance of the human decisions that justify this identity; the decisions stay in their own files.
    a.vstate().leaflets[leafKey].cross_view_review = {group_id: group.group_id, ...group.provenance};
    applied.push({group_id: group.group_id, leaf_key: leafKey, views});
  }
}
// Human visibility answers, addressed by photo and source annotation, applied to whichever leaf holds that box.
const visibilityApplied = [], visibilitySkipped = [];
for (const v of job.visibility || []) {
  const hits = Object.entries(a.vstate().leaflets).filter(([, leaf]) => {
    const box = leaf.bboxes?.[v.key];
    return box && String(box.source_detection?.source_annotation_id) === String(v.source_annotation_id);
  });
  if (hits.length !== 1) { visibilitySkipped.push({...v, reason: hits.length ? 'several_leaves_hold_this_box' : 'box_not_linked_to_a_leaf'}); continue; }
  a.setLeafViewStatus(hits[0][0], v.key, 'visibility', v.value);
  visibilityApplied.push({...v, leaf_key: hits[0][0]});
}
process.stdout.write(JSON.stringify({backup: {...backup, variants: a.store.variants}, applied, skipped,
  visibility_applied: visibilityApplied, visibility_skipped: visibilitySkipped}));
