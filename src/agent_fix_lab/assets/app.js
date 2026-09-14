const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="afl-token"]').content;
let selected = null, detailGeneration = 0, listGeneration = 0, taskGeneration = 0, mutation = false;
function notice(text, error=false) { $('notice').textContent=text; $('notice').className=error?'error':''; }
function show(id,value) { $(id).textContent=typeof value==='string'?value:JSON.stringify(value,null,2); }
async function api(path,body) {
  const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-AFL-Token':token},body:JSON.stringify(body)});
  const data=await response.json();
  if(!response.ok) throw new Error(data.error || JSON.stringify(data.detail) || `Request failed (${response.status})`);
  return data;
}
async function task(name,fn,write=false) {
  if(mutation) return;
  const operation=++taskGeneration;
  if(write) { mutation=true; document.querySelector('main').inert=true; $('import').disabled=true; }
  document.body.dataset.state='loading'; document.body.dataset.operation=name;
  delete document.body.dataset.completed;
  notice(name==='run'?'Running reviewed assertions against both revisions…':'Loading…');
  try { await fn(); if(operation===taskGeneration){document.body.dataset.state='ready'; document.body.dataset.completed=name; notice('Completed: '+name);} }
  catch(e) { if(operation===taskGeneration){document.body.dataset.state='error'; notice(e.message,true);} }
  finally { if(write) { mutation=false; document.querySelector('main').inert=false; $('import').disabled=false; } }
}
async function list() {
  const generation=++listGeneration;
  const rows=await api('/api/cases?q='+encodeURIComponent($('search').value)+'&status='+encodeURIComponent($('status').value));
  if(generation!==listGeneration) return;
  $('cases').replaceChildren();
  for(const row of rows) {
    const button=document.createElement('button'); button.className='case'; button.dataset.caseId=row.id;
    const badge=document.createElement('strong'); badge.textContent=`${row.status.toUpperCase()} · ${row.tool || 'unknown tool'}`;
    const label=document.createElement('span'); label.textContent=row.summary || 'No recorded output';
    const sub=document.createElement('small'); sub.textContent=`${row.unknown.length} missing fields · ${row.cohort} · ${row.split}`;
    button.append(badge,label,sub); button.onclick=()=>task('detail',()=>detail(row.id)); $('cases').append(button);
  }
  $('cases').dataset.state=rows.length?'loaded':'empty';
}
async function detail(id) {
  selected=id; const generation=++detailGeneration;
  const data=await api('/api/cases/'+id);
  if(generation!==detailGeneration || id!==selected) { document.body.dataset.discardedDetails=String(Number(document.body.dataset.discardedDetails || 0)+1); return; }
  $('detail').replaceChildren($('detail-template').content.cloneNode(true));
  $('detail').dataset.caseId=id;
  show('case-title',`${data.observations.observed_status.toUpperCase()} · ${id.slice(0,12)}`);
  show('completeness','Unknown: '+data.observations.unknown.join(', '));
  show('output',data.observations.output);
  show('source',{source:data.observations.source,symptoms:data.observations.symptoms,lineage:data.source_observations});
  show('annotations',{operator_history:data.interpretations,correction_candidates:data.correction_candidates}); show('config',data.configuration_difference);
  show('availability',data.unavailable_reason || 'Only previously reviewed recipes can run.');
  show('results',data.results);
  for(const recipe of data.recipes) { const option=document.createElement('option'); option.value=recipe.id; option.textContent=recipe.expected_behavior; $('recipes').append(option); }
  $('run').disabled=!data.recipes.length;
  $('annotation-form').onsubmit=e=>{e.preventDefault();const body={text:$('correction').value,expected:$('expected').value};task('annotation',async()=>{await api(`/api/cases/${id}/annotations`,body);await detail(id);},true);};
  $('baseline-form').onsubmit=e=>{e.preventDefault();task('baseline',async()=>{const body={logical_path:$('logical-path').value,baseline:JSON.parse($('baseline-json').value),current:JSON.parse($('current-json').value)};await api(`/api/cases/${id}/baseline`,body);await detail(id);},true);};
  $('recipe-form').onsubmit=e=>{e.preventDefault();task('recipe',async()=>{const body={reviewed:$('reviewed').checked,recipe:{schema_version:2,input_contract:$('input-declared').checked?'declared-v1':'unknown',frozen_inputs:JSON.parse($('frozen-inputs').value),case_id:id,repository:$('repo').value,faulty_revision:$('faulty').value,corrected_revision:$('corrected').value,test_file:$('test-file').value,expected_behavior:$('recipe-expected').value,intended_failure:$('failure').value}};const saved=await api('/api/recipes',body);await detail(id);if(selected===id)$('recipes').value=saved.id;},true);};
  $('run').onclick=()=>{const recipe=$('recipes').value;task('run',async()=>{const result=await api(`/api/recipes/${recipe}/run`,{});await detail(id);if(selected===id){show('results',result);$('results').dataset.comparison=result.comparison.status;}},true);};
  $('export').onclick=()=>task('export',async()=>{const report=await api(`/api/cases/${id}/export`);show('export-output',report);const blob=new Blob([JSON.stringify(report,null,2)],{type:'application/json'});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='agent-fix-lab-summary.json';link.click();URL.revokeObjectURL(link.href);});
}
$('search').oninput=()=>task('list',list); $('status').onchange=()=>task('list',list);
$('import').onclick=()=>task('import',async()=>{await api('/api/import',{limit:100});await list();},true);
task('list',list);
