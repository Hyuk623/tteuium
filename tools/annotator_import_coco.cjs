// Runs the editor's own COCO import on a prepared seed so there is one detection schema.
// stdin: {seed, coco, coco_name, frames:[{key,image_file,width,height}], growth, growth_name}
// stdout: {backup, import}. No network, model, upload or browser storage is touched.
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
  this.api = {ui, store, images, importDetections, loadGrowthReference, vstate, membershipCounts};
})();`, context);
const a = context.api;
const seed = job.seed;
a.ui.plant = seed.plant_id;
a.ui.variant = '__all__';
a.store.variants = JSON.parse(JSON.stringify(seed.variants));
for (const f of job.frames) a.images.set(f.key, {key: f.key, name: f.image_file, size: [f.width, f.height]});
const byName = new Map(job.frames.map(f => [f.image_file.toLowerCase(), f]));
const resolve = name => { const f = byName.get(String(name).split(/[\\/]/).pop().toLowerCase()); return f ? {key: f.key, width: f.width, height: f.height} : null; };
const result = a.importDetections(job.coco, job.coco_name, resolve);
if (job.growth) a.loadGrowthReference(job.growth, job.growth_name);
const counts = {};
for (const list of Object.values(a.vstate().membership?.detections || {}))
  for (const d of list) counts[d.class_name] = (counts[d.class_name] || 0) + 1;
process.stdout.write(JSON.stringify({backup: {...seed, variants: a.store.variants},
  import: {imported: result.imported, duplicates: result.duplicates, skipped: result.skipped, detections_by_class: counts}}));
