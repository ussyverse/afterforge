"use strict";
const el = id => document.getElementById(id);
const token = document.querySelector('meta[name="afl-token"]').content;
let selected = null, next = null, busy = false, generation = 0;
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json", "X-AFL-Token": token},
    body: JSON.stringify(body)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Request failed");
  return result;
}
async function action(fn) {
  if (busy) return;
  busy = true;
  document.querySelectorAll("button").forEach(b => b.disabled = true);
  try { await fn(); el("notice").textContent = "Saved locally. No behavior change authorized."; }
  catch (error) { el("notice").textContent = error.message; }
  finally {
    busy = false;
    document.querySelectorAll("button").forEach(b => b.disabled = false);
    el("evaluate-button").disabled = !selected;
    el("review-button").disabled = !selected;
    el("next").disabled = next === null;
  }
}
async function show(id) {
  const current = ++generation;
  const record = await api("/api/interventions/" + encodeURIComponent(id));
  if (current !== generation) return;
  selected = record;
  el("detail").textContent = JSON.stringify(record, null, 2);
  el("authorized").checked = false;
  el("evaluation-id").value = record.evaluations.at(-1)?.id || "";
}
async function listing(offset = 0) {
  const data = await api("/api/interventions?offset=" + offset);
  next = data.next_offset;
  el("proposals").replaceChildren();
  for (const item of data.items) {
    const button = document.createElement("button");
    button.textContent = item.id;
    button.addEventListener("click", () => action(() => show(item.id)));
    el("proposals").append(button);
  }
}
el("refresh").addEventListener("click", () => action(() => listing()));
el("next").addEventListener("click", () => action(() => listing(next)));
el("propose").addEventListener("submit", event => {
  event.preventDefault();
  action(async () => {
    const record = await api("/api/interventions", JSON.parse(el("proposal-json").value));
    await listing(); await show(record.id);
  });
});
el("evaluate").addEventListener("submit", event => {
  event.preventDefault();
  action(async () => {
    if (!selected || !el("authorized").checked) throw new Error("Explicit review required");
    const id = selected.id;
    await api("/api/interventions/" + id + "/evaluate", {candidate_digest: selected.candidate_digest, reviewed: true});
    await show(id);
  });
});
el("review").addEventListener("submit", event => {
  event.preventDefault();
  action(async () => {
    if (!selected) throw new Error("Select a candidate");
    const id = selected.id;
    await api("/api/interventions/" + id + "/review", {
      candidate_digest: selected.candidate_digest, evaluation_id: el("evaluation-id").value,
      decision: el("decision").value, note: el("note").value
    });
    await show(id);
  });
});
action(() => listing());
