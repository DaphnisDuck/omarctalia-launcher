const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {spawnSync} = require('node:child_process');
const m = require('../MenuModel.js');
const parse = value => m.parseMenuJsonc(JSON.stringify(value));
const base = parse({about: {label: 'About', icon: 'i', action: 'show-about', when: 'true'}, apps: {label:'Apps', provider:'apps'}});
test('partial overrides preserve action, label, conditions and provider', () => {
 const merged=m.mergeMenuSources(base,parse({about:{description:'Read more'},apps:{description:'Launch apps'}}));
 assert.equal(merged.items.about.action,'show-about');
 assert.equal(merged.items.about.kind,'action');
 assert.equal(merged.items.about.label,'About');
 assert.equal(merged.items.about.when,'true');
 assert.equal(merged.items.apps.provider,'apps');
 assert.equal(merged.items.about.description,'Read more');
 const cleared=m.mergeMenuSources(base,parse({about:{action:'',when:''}}));
 assert.equal(cleared.items.about.kind,'menu');
});
test('JSONC comments and trailing commas do not damage strings',()=>{
 const text=`{/* block */ "about": {"action":"echo 'https://example.com/a//b,}'", // inline\n "description":"escaped \\\"quote\\\" /* text */",},}`;
 const rows=m.parseMenuJsonc(text);
 assert.equal(rows[0].action,"echo 'https://example.com/a//b,}'");
 assert.equal(rows[0].description,'escaped "quote" /* text */');
 assert.deepEqual(m.parseMenuJsonc('// empty\n'),[]);
 assert.throws(()=>m.parseMenuJsonc('/* unfinished'));
 assert.throws(()=>m.parseMenuJsonc('{"x":'));
});
test('schema and hierarchy reject malformed values and cycles',()=>{
 for(const raw of ['[]','null','{"x":null}','{"x":{"action":7}}','{"x":{"aliases":[7]}}','{"__proto__":{}}']) assert.throws(()=>m.parseMenuJsonc(raw));
 assert.throws(()=>m.mergeMenuSources(parse({'x.y':{}}),[]),/Missing parent/);
 assert.throws(()=>m.mergeMenuSources(parse({x:{parent:'y'},y:{parent:'x'}}),[]),/cycle/);
 assert.throws(()=>m.mergeMenuSources(parse({x:{target:'missing'}}),[]),/target/);
 assert.throws(()=>m.mergeMenuSources(parse({x:{target:'y'},y:{target:'x'}}),[]),/cycle/);
 assert.throws(()=>m.mergeMenuSources(parse({x:{target:'y'},y:{action:'true'}}),[]),/target a menu/);
});
test('installed menu is compatible and all entries have descriptions',()=>{
 const rows=m.parseMenuJsonc(fs.readFileSync('/usr/share/omarchy/default/omarchy/omarchy-menu.jsonc','utf8'));
 const merged=m.mergeMenuSources(rows,[]);
 const scope=vm.createContext({}); vm.runInContext(fs.readFileSync(require.resolve('../MenuDescriptions.js'),'utf8'),scope);
 for(const id of merged.itemOrder){
  if(id==='root')continue;
  const e=merged.items[id], description=scope.describe(e);
  assert.ok(description && description!==`Run ${e.label}` && description!==`Browse ${e.label} options`,id);
 }
});
test('guard IDs are quoted and cannot become shell code',()=>{
 const id="a'; printf BAD; #";
 const script=m.guardScript({[id]:{when:'true'}});
 const result=spawnSync('bash',['-c',script],{encoding:'utf8'});
 assert.equal(result.status,0); assert.equal(result.stdout,`${id}:w:1\n`);
 assert.equal(m.isVisible({},{},{},{id:'x',kind:'action',when:'true'}),false);
 assert.equal(m.isVisible({},{},{x:true},{id:'x',kind:'action',when:'true'}),true);
});
test('dynamic rows replace stale entries without duplicating IDs',()=>{
 const original=m.mergeMenuSources(base,[]);
 const once=m.mergeAppRows(original.items,original.itemOrder,[{id:'apps.x',kind:'app'},{id:'apps.x',kind:'app'}]);
 assert.equal(once.itemOrder.filter(x=>x==='apps.x').length,1);
 const next=m.mergeAppRows(once.items,once.itemOrder,[{id:'apps.y',kind:'app'}]);
 assert.equal(next.items['apps.x'],undefined); assert.ok(next.items['apps.y']); assert.ok(once.items['apps.x']);
});

test('linked menu chains resolve visibility through to their destination',()=>{
 const g=m.mergeMenuSources(parse({a:{target:'b'},b:{target:'c'},c:{provider:'apps',when:'true'}}),[]);
 assert.equal(m.isVisible(g.items,g.itemOrder,{c:true},g.items.a),true);
 assert.equal(m.isVisible(g.items,g.itemOrder,{c:false},g.items.a),false);
});
