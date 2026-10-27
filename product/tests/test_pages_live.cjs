const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
let now=Date.parse('2026-10-28T00:00:00Z');
const NativeDate=Date;
class ClockDate extends NativeDate {constructor(...args){super(...(args.length?args:[now]));}static now(){return now;}}
const nodes=new Map();
const node=()=>({textContent:'',querySelectorAll:()=>[],prepend:()=>{}});
const fixture={generated_at:'2026-10-27T00:00:00Z',state:{Environment:{},Action:{entries:[]},Growth:{measurements:[]}},checks:[]};
const context={Date:ClockDate,Math,Map,JSON,URL,Response,structuredClone,crypto:require('crypto').webcrypto,localStorage:{getItem:()=>null,setItem:()=>{}},location:{origin:'https://example.com'},document:{baseURI:'https://example.com/demo/',getElementById:id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);},createElement:node},window:{fetch:async()=>new Response(JSON.stringify(fixture))}};
vm.runInNewContext(fs.readFileSync('product/pages-adapter.js','utf8'),context);
(async()=>{const fetchState=async()=> (await context.window.fetch('/api/plants/mvp-demo/state?days=30')).json();const a=await fetchState();now+=60000;const b=await fetchState();assert.equal(Date.parse(b.state.Environment.devices[0].latest.observed_at)-Date.parse(a.state.Environment.devices[0].latest.observed_at),60000);assert.ok(b.state.Environment.readings.length<2500);assert.ok(b.state.Environment.readings.every(r=>r.source==='mock'&&r.sensors.humidity_pct>=0&&r.sensors.humidity_pct<=100));assert.equal(b.state.Action.entries.length,0);assert.equal(b.generated_at,fixture.generated_at);console.log('PASS: rolling live fixture, bounded history, provenance, no fabricated actions');})().catch(e=>{console.error(e);process.exitCode=1;});
