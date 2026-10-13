// Direction-pair suggestions are capture-label conventions only, never measured alignment.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');

function app(names) {
  const html = fs.readFileSync(path.join(__dirname, '../leaf_point_annotator.html'), 'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const nodes = new Map(), saved = new Map();
  const context = vm.createContext({crypto, console, setTimeout: () => 0, clearTimeout: () => {},
    IntersectionObserver: class {disconnect(){} observe(){}},
    localStorage: {getItem: key => saved.get(key), setItem: (key, value) => saved.set(key, value)},
    document: {getElementById: id => {
      if (!nodes.has(id)) nodes.set(id, {value: '2', checked: true, hidden: false, textContent: ''});
      return nodes.get(id);
    }},
    window: {devicePixelRatio: 1}
  });
  const shown = [];
  vm.runInContext(script.slice(0, script.indexOf('// Wiring')) + `
    updateSide = () => {}; refreshSelects = () => {}; draw = () => {};
    ui.plant = 'TEST'; sessionId = 'TEST_session';
    this.shown = [];
    this.messages = [];
    toast = message => this.messages.push(message);
    showImage = (pane, key) => { pane.key = key; this.shown.push([pane.index, key]); };
    this.api = {ui, images, panes, captureNumber, suggestedPartners, showSuggestedPartner, allowedKeys};
  })();`, context);
  const a = context.api;
  for (const name of names) a.images.set(name, {name, size: [1000, 800]});
  a.panes.push({key: names[0], index: 0}, {key: names[1], index: 1});
  return {a, shown: context.shown, messages: context.messages};
}

const NAMES = ['dwt_01_20260920_01.png', 'dwt_01_20260920_03.png', 'dwt_01_20260920_11.png',
               'dwt_01_20260920_12.png', 'dwt_01_20260920_21.png', 'dwt_01_20260920_22.png', 'freehand.png'];

test('oblique and side capture labels pair up, with the top views offered after them', () => {
  const {a} = app(NAMES);
  assert.equal(a.captureNumber('dwt_01_20260920_21.png'), '21');
  assert.deepEqual([...a.suggestedPartners('dwt_01_20260920_21.png')],
    ['dwt_01_20260920_11.png', 'dwt_01_20260920_01.png', 'dwt_01_20260920_03.png']);
  assert.deepEqual([...a.suggestedPartners('dwt_01_20260920_12.png')],
    ['dwt_01_20260920_22.png', 'dwt_01_20260920_01.png', 'dwt_01_20260920_03.png']);
  // A top view does not suggest itself, and an unlabelled file suggests nothing at all.
  assert.deepEqual([...a.suggestedPartners('dwt_01_20260920_01.png')], []);
  assert.equal(a.captureNumber('freehand.png'), null);
  assert.deepEqual([...a.suggestedPartners('freehand.png')], []);
});

test('the suggestion opens in the other pane, cycles, and says it is only a label', () => {
  const {a, shown, messages} = app(NAMES);
  a.panes[0].key = 'dwt_01_20260920_21.png';
  a.panes[1].key = null;
  assert.equal(a.showSuggestedPartner(a.panes[0]), 'dwt_01_20260920_11.png');
  assert.deepEqual([...shown.at(-1)], [1, 'dwt_01_20260920_11.png']);
  assert.equal(a.showSuggestedPartner(a.panes[0]), 'dwt_01_20260920_01.png');
  assert.match(messages.at(-1), /측정된 정렬이 아닙니다/);
  assert.equal(a.panes[0].key, 'dwt_01_20260920_21.png');  // the pane the user is working in is untouched
});

test('nothing is guessed when the file names carry no capture label', () => {
  const {a, shown, messages} = app(['freehand.png', 'other.png']);
  assert.equal(a.showSuggestedPartner(a.panes[0]), null);
  assert.equal(shown.length, 0);
  assert.match(messages.at(-1), /짝 번호를 읽지 못했습니다/);
});
