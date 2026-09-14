const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="afl-token"]').content;
let selected = null, draft = null, plan = null, offset = 0, queueOffset = 0, busy = false;
const show = (id, value) => { $(id).textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2); };
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-AFL-Token':token}, body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || JSON.stringify(data.detail));
  return data;
}
async function task(name, work) {
  if (busy) return;
  busy = true; document.querySelector('main').inert = true; document.body.dataset.state = 'loading';
  show('notice', name + '…');
  try { await work(); document.body.dataset.state = 'ready'; show('notice', 'Completed: ' + name); }
  catch (error) { document.body.dataset.state = 'error'; show('notice', error.message); }
  finally { busy = false; document.querySelector('main').inert = false; }
}
async function listing() {
  const rows = await api(`/api/cases?offset=${offset}&limit=10`);
  $('cases').replaceChildren();
  for (const row of rows) {
    const button = document.createElement('button'); button.className = 'case';
    button.textContent = `${row.status.toUpperCase()} · ${row.summary}`;
    button.onclick = () => task('Open case', () => openCase(row.id)); $('cases').append(button);
  }
  $('previous').disabled = offset === 0; $('next').disabled = rows.length < 10;
  await queue();
}
async function queue() {
  const rows = await api(`/api/corrections?status=${$('queue-state').value}&offset=${queueOffset}&limit=10`);
  $('queue').replaceChildren();
  for (const row of rows) {
    const card = document.createElement('article');
    const summary = document.createElement('p'); summary.textContent = `${row.effective_review_status}: ${row.user_message.content}`;
    const evidence = document.createElement('details'), label = document.createElement('summary'), body = document.createElement('pre');
    label.textContent = 'Evidence, unknowns and reviewer history'; body.textContent = JSON.stringify(row, null, 2); evidence.append(label, body);
    const note = document.createElement('textarea'); note.placeholder = 'Operator review rationale (required)';
    card.append(summary, evidence, note);
    for (const decision of ['accepted', 'rejected']) {
      const button = document.createElement('button'); button.textContent = decision === 'accepted' ? 'Accept as operator' : 'Reject as operator';
      button.onclick = () => task('Review correction', async () => { await api(`/api/corrections/${row.id}/review`, {decision, note:note.value}); await queue(); }); card.append(button);
    }
    for (const review of row.reviews) {
      const button = document.createElement('button'); button.textContent = `Retract ${review.reviewer_kind} ${review.decision} ${review.id.slice(0,8)}`;
      button.onclick = () => task('Retract review', async () => { await api(`/api/corrections/${row.id}/review`, {decision:'retracted', note:note.value, retracts:review.id}); await queue(); }); card.append(button);
    }
    if (row.case_id) { const button = document.createElement('button'); button.textContent = 'Open linked case'; button.onclick = () => task('Open case', () => openCase(row.case_id)); card.append(button); }
    $('queue').append(card);
  }
  $('queue-previous').disabled = queueOffset === 0; $('queue-next').disabled = rows.length < 10;
}
function renderDraft(value) {
  draft = value; show('assertion', value ? value.assertion : 'Create a draft first.');
  show('frozen', value ? value.recipe.frozen_inputs : []); show('proposal', value || {});
  show('unknowns', value ? 'Derived reduction, not reconstruction. Unknown: ' + value.unknowns.join('; ') : '');
  $('authorize').disabled = !value; $('reviewed').checked = false; $('declared').checked = false;
}
async function openCase(id) {
  selected = id; plan = null; $('retain').disabled = true; show('target-plan', ''); show('retained', '');
  const data = await api('/api/guided/' + encodeURIComponent(id));
  show('title', `${data.detail.case.provenance.toUpperCase()} · ${id.slice(0,12)}`);
  show('next-action', 'Next action: ' + data.next_action); show('evidence', data.detail.observations.output);
  renderDraft(data.drafts.length ? data.drafts[data.drafts.length - 1] : null);
  $('recipes').replaceChildren();
  for (const recipe of data.detail.recipes) { const option = document.createElement('option'); option.value = recipe.id; option.textContent = recipe.expected_behavior; $('recipes').append(option); }
  $('run').disabled = !$('recipes').value; $('plan').disabled = !$('recipes').value;
  show('comparison', data.comparison.status.toUpperCase() + ': ' + (data.comparison.reason || 'No comparison yet'));
  show('results', data.detail.results);
}
$('demo').onclick = () => task('Create synthetic demo', async () => { const value = await api('/api/demo', {}); await listing(); await openCase(value.case_id); });
$('scan').onclick = () => task('Scan next bounded page', async () => { await api('/api/import', {limit:100}); await listing(); });
$('previous').onclick = () => task('Previous cases', async () => { offset = Math.max(0, offset - 10); await listing(); });
$('next').onclick = () => task('Next cases', async () => { offset += 10; await listing(); });
$('queue-state').onchange = () => task('Review queue', async () => { queueOffset = 0; await queue(); });
$('queue-previous').onclick = () => task('Previous reviews', async () => { queueOffset = Math.max(0, queueOffset - 10); await queue(); });
$('queue-next').onclick = () => task('Next reviews', async () => { queueOffset += 10; await queue(); });
$('draft-form').onsubmit = event => { event.preventDefault(); task('Generate draft', async () => {
  if (!selected) throw new Error('Select a case first');
  const value = await api('/api/drafts', {case_id:selected, repository:$('repository').value, faulty_revision:$('faulty').value, corrected_revision:$('corrected').value, module:$('module').value, function:$('function').value, expected_behavior:$('expected').value, intended_failure:$('failure').value, examples:JSON.parse($('examples').value)});
  renderDraft(value);
}); };
$('approval-form').onsubmit = event => { event.preventDefault(); task('Authorize reviewed draft', async () => {
  const recipe = await api(`/api/drafts/${draft.id}/authorize`, {approve_digest:draft.draft_digest, reviewed:$('reviewed').checked, declared_inputs:$('declared').checked});
  await openCase(selected); $('recipes').value = recipe.id;
}); };
$('run').onclick = () => task('Run regression', async () => { const result = await api(`/api/recipes/${$('recipes').value}/run`, {}); show('results', result); show('comparison', result.comparison.status.toUpperCase() + ': ' + result.comparison.reason); $('comparison').dataset.status = result.comparison.status; });
$('plan-form').onsubmit = event => { event.preventDefault(); task('Freeze explicit target plan', async () => { plan = await api('/api/retained-plan', {recipe_id:$('recipes').value, target_revision:$('target').value, reviewed_data_changes:JSON.parse($('data-changes').value)}); show('target-plan', plan); $('target-reviewed').checked = false; $('retain').disabled = false; }); };
$('retain-form').onsubmit = event => { event.preventDefault(); task('Run retained archive check', async () => { const receipt = await api(`/api/retained-check/${plan.id}`, {approve_digest:plan.plan_digest, reviewed:$('target-reviewed').checked}); show('retained', receipt); $('retained').dataset.status = receipt.status; }); };
task('Load guided workflow', listing);
