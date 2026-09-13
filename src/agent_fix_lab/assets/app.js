const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="afl-token"]').content;
let selected = null;
function notice(text, error=false) { $('notice').textContent=text; $('notice').className=error?'error':''; }
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-AFL-Token':token},body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || data.detail || `Request failed (${response.status})`);
  return data;
}
function show(id, value) { $(id).textContent = typeof value === 'string' ? value : JSON.stringify(value,null,2); }
async function action(fn) { try { notice('Working…'); await fn(); notice('Operation completed. Inspect the evidence below.'); } catch(e) { notice(e.message,true); } }
async function list() {
  notice('Loading cases…');
  const rows=await api('/api/cases?q='+encodeURIComponent($('search').value)+'&status='+encodeURIComponent($('status').value));
  $('cases').replaceChildren();
  for(const row of rows) {
    const button=document.createElement('button'); button.className='case';
    const badge=document.createElement('strong'); badge.textContent=`${row.status.toUpperCase()} · ${row.tool || 'unknown tool'}`;
    const label=document.createElement('span'); label.textContent=row.summary || 'No recorded output';
    const sub=document.createElement('small'); sub.textContent=`${row.unknown.length} missing fields · ${row.cohort} · ${row.split}`;
    button.append(badge,label,sub); button.onclick=()=>action(()=>detail(row.id)); $('cases').append(button);
  }
  notice(rows.length ? `${rows.length} cases. Process facts and interpretations remain separate.` : 'No matching cases. Change filters or import local history.');
}
async function detail(id) {
  selected=id; const data=await api('/api/cases/'+id);
  $('detail').replaceChildren($('detail-template').content.cloneNode(true));
  show('case-title',`${data.observations.observed_status.toUpperCase()} · ${id.slice(0,12)}`);
  show('completeness','Unknown: '+data.observations.unknown.join(', '));
  show('output',data.observations.output); show('source',{source:data.observations.source,symptoms:data.observations.symptoms});
  show('annotations',data.interpretations); show('config',data.configuration_difference);
  show('availability',data.unavailable_reason || 'Only previously reviewed recipes can run.');
  show('results',data.results);
  for(const recipe of data.recipes) { const option=document.createElement('option'); option.value=recipe.id; option.textContent=recipe.expected_behavior; $('recipes').append(option); }
  $('run').disabled=!data.recipes.length;
  $('annotation-form').onsubmit=e=>{e.preventDefault();action(async()=>{await api(`/api/cases/${id}/annotations`,{text:$('correction').value,expected:$('expected').value});await detail(id);});};
  $('baseline-form').onsubmit=e=>{e.preventDefault();action(async()=>{await api(`/api/cases/${id}/baseline`,{logical_path:$('logical-path').value,baseline:JSON.parse($('baseline-json').value),current:JSON.parse($('current-json').value)});await detail(id);});};
  $('recipe-form').onsubmit=e=>{e.preventDefault();action(async()=>{await api('/api/recipes',{reviewed:$('reviewed').checked,recipe:{case_id:id,repository:$('repo').value,faulty_revision:$('faulty').value,corrected_revision:$('corrected').value,test_file:$('test-file').value,expected_behavior:$('recipe-expected').value,intended_failure:$('failure').value}});await detail(id);});};
  $('run').onclick=()=>action(async()=>{const recipe=$('recipes').value;$('run').disabled=true;const result=await api(`/api/recipes/${recipe}/run`,{});await detail(id);show('results',result);});
  $('export').onclick=()=>action(async()=>{const report=await api(`/api/cases/${id}/export`);show('export-output',report);const blob=new Blob([JSON.stringify(report,null,2)],{type:'application/json'});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='agent-fix-lab-summary.json';link.click();URL.revokeObjectURL(link.href);});
}
$('search').oninput=()=>action(list); $('status').onchange=()=>action(list);
$('import').onclick=()=>action(async()=>{const stats=await api('/api/import',{limit:100,after:Date.now()/1000-86400});await list();notice(JSON.stringify(stats));});
action(list);
