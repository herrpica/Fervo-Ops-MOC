/* Fervo OMOC — build-free React front end (HTM + React UMD, no toolchain).
   Talks to the FastAPI backend under /api. */
const html = htm.bind(React.createElement);
const { useState, useEffect, useCallback } = React;

/* ---------------- client-side compute mirror (live badges before save) ---------------- */
const maxRisk = m => (m.risk_items || []).reduce((mx, r) =>
  (r.severity && r.likelihood) ? Math.max(mx, r.severity * r.likelihood) : mx, 0);
const approvalLevel = m => maxRisk(m) > 8 ? "CEO" : "VP Operations";
const phaLevel = m => maxRisk(m) > 12 ? "HAZOP" : "What-If Analysis";
const riskLevel = m => { const x = maxRisk(m); return x >= 15 ? "HIGH" : (x >= 8 ? "MEDIUM" : "LOW"); };
const priority = m => approvalLevel(m) === "VP Operations" ? "Normal" : "High";
const flagType = m => m.emergency ? "Emergency" : (m.temporary ? "Temporary" : "Standard");
const omocRequired = m => (m.checklist || []).some(c => c.answer === "Y") ? "Y" : "N";
function stepComplete(m, i) {
  if (i === 0) return (m.checklist || []).length >= 10;
  if (i === 1) return !!(m.change_name && m.initiator && m.date_requested && m.description && m.justification);
  if (i === 2) return (m.risk_items || []).length > 0 && m.risk_items.every(r => r.severity && r.likelihood);
  if (i === 3) return (m.action_items || []).length > 0 || (m.impl_reqs || []).length > 0 || m.status === "Complete";
  if (i === 4) return true;
  if (i === 5) return m.workflow_state === "Approved" || m.workflow_state === "Closed";
  if (i === 6) return m.workflow_state === "Closed";
  return false;
}
const progress = m => [0,1,2,3,4,5,6].filter(i => stepComplete(m, i)).length;
const scoreColor = v => v === 0 ? "var(--slate)" : (v >= 15 ? "var(--earth)" : (v >= 8 ? "var(--sand)" : "var(--green)"));

/* ---------------- API ---------------- */
const API = {
  reference: () => fetch("/api/reference").then(r => r.json()),
  dashboard: () => fetch("/api/dashboard").then(r => r.json()),
  get: id => fetch("/api/mocs/" + id).then(r => r.json()),
  create: () => fetch("/api/mocs", { method: "POST" }).then(r => r.json()),
  update: (id, body) => fetch("/api/mocs/" + id, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(r => r.json()),
  del: id => fetch("/api/mocs/" + id, { method: "DELETE" }).then(r => r.json()),
};

const STEPS = [
  ["Checklist", "Screening"], ["Change Request", "Description & metadata"],
  ["Risk & Stakeholders", "Scoring & endorsers"], ["Actions & Implementation", "Tasks & requirements"],
  ["Attachments", "Supporting docs"], ["Endorsements & Approval", "Sign-offs"], ["Closure", "Verify & close"],
];
let REF = {};

/* ---------------- small components ---------------- */
const Badge = ({ kind, children }) => html`<span class="badge ${kind}">${children}</span>`;
const flagKind = m => flagType(m) === "Emergency" ? "earth" : (flagType(m) === "Temporary" ? "sand" : "gray");
const STATE_KIND = { "Draft": "gray", "Submitted for Endorsement": "cobalt", "Revision Requested": "earth", "Pending Final Approval": "sand", "Approved": "green", "Closed": "green" };
const stateKind = s => STATE_KIND[s] || "gray";

/* ---------------- Dashboard ---------------- */
function Dashboard() {
  const [d, setD] = useState(null);
  const load = useCallback(() => API.dashboard().then(setD), []);
  useEffect(() => { load(); }, [load]);
  if (!d) return html`<div class="wrap"><div class="loading">Loading dashboard…</div></div>`;

  const newMoc = () => API.create().then(m => { location.hash = "#/moc/" + m.id + "/0"; });
  const del = (id, name) => { if (confirm("Delete " + name + "? This cannot be undone.")) API.del(id).then(load); };
  const scrollTo = id => { const el = document.getElementById(id); if (el) el.scrollIntoView({ behavior: "smooth" }); };

  const mocRow = (m, showProg) => html`<tr key=${m.id}>
    <td><strong>${m.change_number}</strong></td>
    <td>${m.change_name || "(untitled)"}</td>
    <td><${Badge} kind=${stateKind(m.workflow_state)}>${m.workflow_state}<//>${m.revision_count ? html` <span class="mini">rev ${m.revision_count}</span>` : ""}</td>
    <td><${Badge} kind=${m.flag_type === "Emergency" ? "earth" : (m.flag_type === "Temporary" ? "sand" : "gray")}>${m.flag_type}<//></td>
    <td><${Badge} kind=${m.risk_level.toLowerCase()}>${m.risk_level}<//></td>
    <td><${Badge} kind=${m.approval_level === "CEO" ? "high" : "cobalt"}>${m.approval_level}<//></td>
    <td>${showProg
      ? html`<div class="prog"><div class="bar"><span style=${{ width: (m.progress / 7 * 100) + "%" }}></span></div><div class="txt">${m.progress}/7</div></div>`
      : html`<span class="mini">${m.closure_date || "—"}</span>`}</td>
    <td><div class="row-actions">
      <button class="icon-btn" onClick=${() => location.hash = "#/moc/" + m.id + "/0"}>Open</button>
      <button class="icon-btn del" onClick=${() => del(m.id, m.change_number)}>Delete</button>
    </div></td>
  </tr>`;

  const table = (anchor, heading, list, showProg) => html`
    <div class="sec-head" id=${anchor}><h2>${heading}</h2></div>
    <div class="card table-card">
      ${list.length === 0 ? html`<div class="empty">No ${heading.toLowerCase()} yet.</div>` : html`
      <table><thead><tr>
        <th>Change #</th><th>Change Name</th><th>Workflow State</th><th>Type</th><th>Risk</th><th>Approval</th>
        <th>${showProg ? "Progress" : "Closed"}</th><th></th>
      </tr></thead><tbody>${list.map(m => mocRow(m, showProg))}</tbody></table>`}
    </div>`;

  return html`<div class="wrap">
    <div class="sec-head"><h2>Dashboard</h2><button class="btn lg" onClick=${newMoc}>+ Initiate New MOC</button></div>
    <div class="kpis">
      <div class="kpi" onClick=${() => scrollTo("sec-active")}><div class="num">${d.active_count}</div><div class="lbl">Active MOCs</div></div>
      <div class="kpi complete" onClick=${() => scrollTo("sec-complete")}><div class="num">${d.complete_count}</div><div class="lbl">Completed MOCs</div></div>
      <div class="kpi late-actions" onClick=${() => scrollTo("sec-la")}><div class="num">${d.late_action_items.length}</div><div class="lbl">Late Action Items</div></div>
      <div class="kpi late-signoffs" onClick=${() => scrollTo("sec-ls")}><div class="num">${d.late_signoffs.length}</div><div class="lbl">Late Sign-offs</div></div>
    </div>
    ${table("sec-active", "Active MOCs", d.active, true)}
    ${table("sec-complete", "Completed MOCs", d.complete, false)}

    <div class="sec-head" id="sec-la"><h2>Late Action Items</h2></div>
    <div class="card table-card">
      ${d.late_action_items.length === 0 ? html`<div class="empty">No overdue action items.</div>` : html`
      <table><thead><tr><th>MOC</th><th>Type</th><th>Item</th><th>Assigned To</th><th>Due</th><th>Days Late</th><th></th></tr></thead>
      <tbody>${d.late_action_items.map((x, i) => html`<tr key=${i}>
        <td><strong>${x.moc}</strong></td><td><${Badge} kind=${x.kind === "Action" ? "cobalt" : "gray"}>${x.kind}<//></td>
        <td>${x.item}</td><td>${x.assigned_to}</td><td class="tag-late">${x.due}</td><td class="tag-late">${x.days_late}d</td>
        <td><button class="icon-btn" onClick=${() => location.hash = "#/moc/" + x.moc_id + "/3"}>Open</button></td></tr>`)}</tbody></table>`}
    </div>

    <div class="sec-head" id="sec-ls"><h2>Late Sign-offs</h2></div>
    <div class="card table-card">
      ${d.late_signoffs.length === 0 ? html`<div class="empty">No sign-offs past the ${REF.signoff_sla_days}-day SLA.</div>` : html`
      <table><thead><tr><th>Person</th><th>Role</th><th>MOC</th><th>Change Name</th><th>Days Late</th><th></th></tr></thead>
      <tbody>${d.late_signoffs.map((x, i) => html`<tr key=${i}>
        <td><strong>${x.person}</strong></td>
        <td><${Badge} kind=${x.role === "Final Approver" ? "high" : "sand"}>${x.role}<//> <span class="mini">${x.department}</span></td>
        <td><strong>${x.moc}</strong></td><td></td><td class="tag-late">${x.age}d</td>
        <td><div class="row-actions">
          <button class="icon-btn" onClick=${() => remind(x)} disabled=${!x.email}>Remind</button>
          <button class="icon-btn" onClick=${() => location.hash = "#/moc/" + x.moc_id + "/5"}>Open</button>
        </div></td></tr>`)}</tbody></table>`}
    </div>
    <p class="mini" style=${{ marginTop: "18px" }}>Action items are late when past due and not Complete. Sign-offs are late when an active MOC has gone ${REF.signoff_sla_days}+ days since Date Requested without that person's initials/approval.</p>
  </div>`;
}
function remind(x) {
  const subj = "Action needed: MOC " + x.moc + " awaiting your sign-off";
  const body = "Hi " + x.person + ",\n\nMOC " + x.moc + " is awaiting your " + x.role.toLowerCase() + " sign-off (" + x.age + " days). Please review and approve.\n\nThank you,\nMOC Coordinator";
  location.href = "mailto:" + encodeURIComponent(x.email) + "?subject=" + encodeURIComponent(subj) + "&body=" + encodeURIComponent(body);
}

/* ---------------- Wizard ---------------- */
function Wizard({ id, step, user }) {
  const [m, setM] = useState(null);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState(null);
  const [showLog, setShowLog] = useState(false);
  useEffect(() => { API.get(id).then(setM); }, [id]);
  if (!m) return html`<div class="wrap"><div class="loading">Loading MOC…</div></div>`;

  const save = async (overrides) => {
    const body = { ...m, ...(overrides || {}) };
    const res = await API.update(id, body);
    setM(res); setSaved(true); setTimeout(() => setSaved(false), 1500);
    return res;
  };
  const upd = fn => setM(prev => { const n = JSON.parse(JSON.stringify(prev)); fn(n); return n; });
  const go = s => { location.hash = "#/moc/" + id + "/" + s; };
  // Workflow transition: POST to an action endpoint, refresh from server.
  const act = async (path, body) => {
    body = body || {};
    if (path === "endorse" || path === "final-decision" || path === "clear-signoff") {
      body.actor_name = (user && user.name) || ""; body.actor_email = (user && user.email) || "";
    }
    const res = await fetch("/api/mocs/" + id + "/" + path, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body) });
    if (!res.ok) { const e = await res.json().catch(() => ({})); setErr(e.detail || "Action failed"); return null; }
    const data = await res.json(); setM(data); setErr(null); setSaved(true); setTimeout(() => setSaved(false), 1500);
    return data;
  };

  const i = step;
  const stepBody = [Checklist, ChangeRequest, RiskStake, Actions, Attachments, Endorsements, Closure][i];

  // Content lock: the change is editable only in Draft / Revision Requested; closure
  // fields only while Approved. Other states are read-only (enforced server-side too).
  const contentEditable = m.workflow_state === "Draft" || m.workflow_state === "Revision Requested";
  const closureEditable = m.workflow_state === "Approved";
  const lockInputs = (i <= 4 && !contentEditable) || (i === 6 && !closureEditable);
  const stepEditable = (i <= 5 && contentEditable) || (i === 6 && closureEditable);

  const next = async () => {
    const e1 = validate(m, i);
    if (e1) { setErr(e1); return; }
    setErr(null);
    if (stepEditable) await save();
    if (i < 6) go(i + 1);
  };
  const finish = async () => {
    await save();                 // persist closure edits first
    const res = await act("close");   // server validates Approved + all verified + date
    if (res && res.workflow_state === "Closed") location.hash = "#/dashboard";
  };

  return html`
    <div class="wiz-head">
      <div class="crumbs"><a onClick=${() => location.hash = "#/dashboard"}>Dashboard</a> › ${m.change_number}
        <span style=${{ flex: 1 }}></span>
        <button class="btn ghost" style=${{ padding: "5px 12px", fontSize: "12px" }} onClick=${() => window.print()}>🖨 Print</button>
      </div>
      <div class="name">${m.change_name || "Untitled Change"}</div>
      <div class="meta">
        <${Badge} kind=${stateKind(m.workflow_state)}>${m.workflow_state}<//>
        <${Badge} kind=${flagKind(m)}>${flagType(m)}<//>
        <${Badge} kind=${omocRequired(m) === "Y" ? "cobalt" : "gray"}>OMOC ${omocRequired(m) === "Y" ? "Required" : "Not Required"}<//>
        <${Badge} kind=${riskLevel(m).toLowerCase()}>Risk: ${riskLevel(m)}<//>
        <${Badge} kind=${approvalLevel(m) === "CEO" ? "high" : "cobalt"}>${approvalLevel(m)} Approval<//>
        <${Badge} kind=${priority(m) === "High" ? "high" : "gray"}>Priority: ${priority(m)}<//>
      </div>
    </div>
    <div class="wrap"><div class="wiz-layout">
      <div class="rail">
        <div class="rail-h">MOC Steps</div>
        ${STEPS.map((s, idx) => html`<div key=${idx} class="step ${idx === i ? "current" : ""} ${stepComplete(m, idx) ? "done" : ""}" onClick=${() => go(idx)}>
          <div class="marker">${stepComplete(m, idx) ? "✓" : (idx + 1)}</div>
          <div><div class="s-title">${s[0]}</div><div class="s-sub">${s[1]}</div></div></div>`)}
        <div class="rail-progress">${progress(m)} of 7 steps complete</div>
      </div>
      <div class="panel">
        ${err && html`<div class="alert red">${err}</div>`}
        ${(i <= 4 && !contentEditable) && html`<div class="alert amber">🔒 This MOC is <strong>${m.workflow_state}</strong>. The change is locked — content can only be edited while Draft or Revision Requested, so endorsers and approvers always review the version they signed.</div>`}
        ${(i === 6 && !closureEditable) && html`<div class="alert amber">🔒 Closure becomes available once the MOC is <strong>Approved</strong> (current state: ${m.workflow_state}).</div>`}
        ${i === 5
          ? html`<${stepBody} m=${m} upd=${upd} save=${save} act=${act} editable=${contentEditable} />`
          : html`<fieldset class="lockable" disabled=${lockInputs}><${stepBody} m=${m} upd=${upd} save=${save} act=${act} /></fieldset>`}
        <div class="panel-foot">
          <button class="btn ghost" disabled=${i === 0} onClick=${() => go(i - 1)}>← Back</button>
          <div style=${{ display: "flex", gap: "8px" }}>
            ${stepEditable && html`<button class="btn secondary" onClick=${() => save()}>Save</button>`}
            ${i < 6
              ? html`<button class="btn" onClick=${next}>${stepEditable ? "Save & Continue →" : "Continue →"}</button>`
              : (closureEditable
                  ? html`<button class="btn" onClick=${finish}>Complete & Close MOC</button>`
                  : html`<span class="mini">Closure available after approval</span>`)}
          </div>
        </div>
      </div>
    </div></div>

    <div class="wrap" style=${{ paddingTop: 0 }}>
      <div class="card" style=${{ padding: "14px 18px" }}>
        <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }} onClick=${() => setShowLog(!showLog)}>
          <strong style=${{ color: "var(--cobalt)" }}>Activity Log (${(m.audit_events || []).length})</strong>
          <span class="mini">${showLog ? "▲ hide" : "▼ show"}</span>
        </div>
        ${showLog && html`<div style=${{ marginTop: "10px" }}>
          ${(m.audit_events || []).length === 0 ? html`<div class="mini">No activity yet.</div>`
            : (m.audit_events || []).map((ev, k) => html`<div key=${k} style=${{ display: "flex", gap: "10px", padding: "7px 0", borderTop: k ? "1px solid var(--border)" : "none" }}>
              <span class="badge ${ev.event_type === "endorsement" ? "cobalt" : (ev.event_type === "final_decision" ? "sand" : (ev.event_type === "closed" ? "green" : "gray"))}" style=${{ flex: "none" }}>${ev.event_type}</span>
              <div><div style=${{ fontSize: "13px" }}>${ev.summary}</div><div class="mini">${(ev.timestamp || "").replace("T", " ").slice(0, 16)}${ev.actor ? (" · " + ev.actor) : ""}</div></div>
            </div>`)}
        </div>`}
      </div>
    </div>
    ${saved && html`<div class="saving">✓ Saved</div>`}`;
}
function validate(m, i) {
  if (i === 1) {
    const miss = [];
    if (!m.change_name) miss.push("Change Name");
    if (!m.initiator) miss.push("Initiator");
    if (!m.date_requested) miss.push("Date Requested");
    if (!m.description) miss.push("Description");
    if (!m.justification) miss.push("Justification");
    if (miss.length) return "Please complete: " + miss.join(", ") + ".";
  }
  if (i === 2 && !(m.risk_items.length && m.risk_items.every(r => r.severity && r.likelihood)))
    return "Score Severity and Likelihood for all risk questions.";
  return null;
}

/* ---------- Step 1: Checklist ---------- */
function Checklist({ m, upd }) {
  const setC = (idx, v) => upd(n => { n.checklist.find(c => c.idx === idx).answer = v; });
  const yn = (val, on) => html`<select class="yn" value=${val} onChange=${e => on(e.target.value)}>
    <option value="N">No</option><option value="Y">Yes</option></select>`;
  return html`<div>
    <h2>Step 1 — Screening Checklist</h2>
    <p class="step-intro">Answer each question to determine whether an OMOC is required and whether it is Emergency or Temporary.</p>
    ${omocRequired(m) === "Y"
      ? html`<div class="alert amber">An <strong>OMOC is required</strong> — one or more items were answered "Yes".</div>`
      : html`<div class="alert green">No checklist items triggered — review with the MOC Coordinator.</div>`}
    <div class="card table-card" style=${{ marginBottom: "18px" }}>
      <table class="qtable"><thead><tr><th>Category</th><th>Question</th><th class="rs-cell">Y/N</th></tr></thead>
      <tbody>${m.checklist.map(c => html`<tr key=${c.idx}>
        <td class="cat">${c.category}</td><td class="q">${c.question}</td>
        <td class="rs-cell">${yn(c.answer, v => setC(c.idx, v))}</td></tr>`)}</tbody></table>
    </div>
    <h3>Timing</h3>
    <div class="card table-card"><table class="qtable"><tbody>
      <tr><td class="q">Is the change temporary (defined reversion/reevaluation date)?</td>
        <td class="rs-cell">${yn(m.temporary ? "Y" : "N", v => upd(n => n.temporary = v === "Y"))}</td></tr>
      <tr><td class="q">Does this change require immediate implementation due to an emergency?</td>
        <td class="rs-cell">${yn(m.emergency ? "Y" : "N", v => upd(n => n.emergency = v === "Y"))}</td></tr>
    </tbody></table></div></div>`;
}

/* ---------- Step 2: Change Request ---------- */
function ChangeRequest({ m, upd }) {
  const f = (k, v) => upd(n => n[k] = v);
  const ci = (k, val) => html`<div class="ci"><div class="k">${k}</div><div class="v">${val}</div></div>`;
  return html`<div>
    <h2>Step 2 — Change Request</h2>
    <p class="step-intro">Document the change, who is requesting it, and why. Priority and flags calculate automatically.</p>
    <div class="computebox"><div class="compute-grid">
      ${ci("Change Number", m.change_number)}${ci("Priority", priority(m))}
      ${ci("Emergency / Temporary", flagType(m) === "Standard" ? "None" : flagType(m))}${ci("OMOC Required", omocRequired(m) === "Y" ? "Yes" : "No")}
    </div></div>
    <div class="grid2">
      <div class="field"><label>Operating Unit</label><input type="text" value=${m.operating_unit || ""} onChange=${e => f("operating_unit", e.target.value)}/></div>
      <div class="field"><label>Change Name *</label><input type="text" value=${m.change_name || ""} onChange=${e => f("change_name", e.target.value)}/></div>
      <div class="field"><label>Initiator *</label><${PersonSelect} email=${m.initiator_email} onPick=${p => upd(n => { n.initiator = p.name; n.initiator_email = p.email; })}/></div>
      <div class="field"><label>Date Requested *</label><input type="date" value=${m.date_requested || ""} onChange=${e => f("date_requested", e.target.value)}/></div>
    </div>
    <div class="field"><label>Change Description *</label><textarea onChange=${e => f("description", e.target.value)} value=${m.description || ""}></textarea></div>
    <div class="field"><label>Change Justification *</label><textarea onChange=${e => f("justification", e.target.value)} value=${m.justification || ""}></textarea></div></div>`;
}

/* ---------- Step 3: Risk & Stakeholders ---------- */
function RiskStake({ m, upd }) {
  const setR = (idx, k, v) => upd(n => { const r = n.risk_items.find(x => x.idx === idx); r[k] = v ? Number(v) : null; });
  const setS = (idx, k, v) => upd(n => { const s = n.stakeholders.find(x => x.idx === idx); s[k] = v; });
  const sel = (val, on, opts) => html`<select value=${val || ""} onChange=${e => on(e.target.value)}>
    ${opts.map((lbl, k) => html`<option key=${k} value=${k === 0 ? "" : k}>${k === 0 ? "—" : lbl}</option>`)}</select>`;
  const ci = (k, val) => html`<div class="ci"><div class="k">${k}</div><div class="v">${val}</div></div>`;
  return html`<div>
    <h2>Step 3 — Risk & Stakeholders</h2>
    <p class="step-intro">Score Severity (1–5) × Likelihood (1–5). Approval routing and PHA update from your highest score.</p>
    <div class="computebox"><div class="compute-grid">
      ${ci("Max Risk Score", maxRisk(m) || "–")}${ci("Risk Level", riskLevel(m))}${ci("Approval Required", approvalLevel(m))}${ci("PHA Required", phaLevel(m))}
    </div></div>
    <h3>Risk Assessment</h3>
    <div class="card table-card" style=${{ marginBottom: "22px" }}>
      <table class="qtable"><thead><tr><th>Category</th><th>Question</th><th class="rs-cell">Severity</th><th class="rs-cell">Likelihood</th><th class="rs-cell">Score</th></tr></thead>
      <tbody>${m.risk_items.map(r => { const v = (r.severity && r.likelihood) ? r.severity * r.likelihood : 0; return html`<tr key=${r.idx}>
        <td class="cat">${r.category}</td><td class="q">${r.question}</td>
        <td class="rs-cell">${sel(r.severity, v2 => setR(r.idx, "severity", v2), REF.severity)}</td>
        <td class="rs-cell">${sel(r.likelihood, v2 => setR(r.idx, "likelihood", v2), REF.likelihood)}</td>
        <td class="rs-cell"><span class="rscore" style=${{ background: scoreColor(v) }}>${v || "–"}</span></td></tr>`; })}</tbody></table>
    </div>
    <h3>Stakeholder Analysis</h3>
    <p class="mini" style=${{ marginTop: "-2px" }}>Departments marked Impacted = Yes are routed as endorsers in Step 6.</p>
    <div class="card table-card"><table><thead><tr><th>Department</th><th class="rs-cell">Impacted?</th><th>Endorser Name</th><th>Endorser Email</th></tr></thead>
    <tbody>${m.stakeholders.map(s => html`<tr key=${s.idx}>
      <td>${s.department}</td>
      <td class="rs-cell"><select class="yn" value=${s.impacted ? "Y" : "N"} onChange=${e => setS(s.idx, "impacted", e.target.value === "Y")}><option value="N">No</option><option value="Y">Yes</option></select></td>
      <td><${PersonSelect} email=${s.endorser_email} onPick=${p => upd(n => { const st = n.stakeholders.find(x => x.idx === s.idx); st.endorser_name = p.name; st.endorser_email = p.email; })}/></td>
      <td class="mini">${s.endorser_email || ""}</td></tr>`)}</tbody></table></div></div>`;
}

/* ---------- Step 4: Actions & Implementation ---------- */
function Actions({ m, upd }) {
  const setA = (i, k, v) => upd(n => n.action_items[i][k] = v);
  const setI = (i, k, v) => upd(n => n.impl_reqs[i][k] = v);
  const stsel = (val, on) => html`<select value=${val} onChange=${e => on(e.target.value)}>${REF.action_status.map(s => html`<option key=${s} value=${s}>${s}</option>`)}</select>`;
  return html`<div>
    <h2>Step 4 — Actions & Implementation</h2>
    <p class="step-intro">Define action items and implementation requirements. Items past due appear on the dashboard as Late Action Items.</p>
    <h3>Action Items</h3>
    <div class="card table-card"><table><thead><tr><th>#</th><th>Type</th><th>Description</th><th>Assigned To</th><th>Due</th><th>Status</th><th></th></tr></thead>
    <tbody>${m.action_items.length ? m.action_items.map((a, i) => html`<tr class="repeater-row" key=${i}>
      <td>${i + 1}</td>
      <td><input type="text" value=${a.type || ""} onChange=${e => setA(i, "type", e.target.value)}/></td>
      <td><input type="text" value=${a.description || ""} onChange=${e => setA(i, "description", e.target.value)}/></td>
      <td><${PersonSelect} email=${a.assigned_email} onPick=${p => upd(n => { n.action_items[i].assigned_to = p.name; n.action_items[i].assigned_email = p.email; })}/></td>
      <td style=${{ width: "130px" }}><input type="date" value=${a.due_date || ""} onChange=${e => setA(i, "due_date", e.target.value)}/></td>
      <td style=${{ width: "120px" }}>${stsel(a.status, v => setA(i, "status", v))}</td>
      <td><button class="del-x" onClick=${() => upd(n => n.action_items.splice(i, 1))}>×</button></td></tr>`)
      : html`<tr><td colSpan="7" class="empty">No action items yet.</td></tr>`}</tbody></table></div>
    <div class="addrow"><button class="btn secondary" onClick=${() => upd(n => n.action_items.push({ type: "", description: "", assigned_to: "", due_date: "", status: "Not Started", comments: "" }))}>+ Add Action Item</button></div>

    <h3 style=${{ marginTop: "26px" }}>Implementation Requirements</h3>
    <div class="card table-card"><table><thead><tr><th>#</th><th>Category</th><th>Requirement</th><th>Assigned To</th><th>Due</th><th>Status</th><th>Verification</th><th></th></tr></thead>
    <tbody>${m.impl_reqs.length ? m.impl_reqs.map((a, i) => html`<tr class="repeater-row" key=${i}>
      <td>${i + 1}</td>
      <td><input type="text" value=${a.category || ""} onChange=${e => setI(i, "category", e.target.value)}/></td>
      <td><input type="text" value=${a.requirement || ""} onChange=${e => setI(i, "requirement", e.target.value)}/></td>
      <td><${PersonSelect} email=${a.assigned_email} onPick=${p => upd(n => { n.impl_reqs[i].assigned_to = p.name; n.impl_reqs[i].assigned_email = p.email; })}/></td>
      <td style=${{ width: "130px" }}><input type="date" value=${a.due_date || ""} onChange=${e => setI(i, "due_date", e.target.value)}/></td>
      <td style=${{ width: "120px" }}>${stsel(a.status, v => setI(i, "status", v))}</td>
      <td><input type="text" value=${a.verification || ""} onChange=${e => setI(i, "verification", e.target.value)}/></td>
      <td><button class="del-x" onClick=${() => upd(n => n.impl_reqs.splice(i, 1))}>×</button></td></tr>`)
      : html`<tr><td colSpan="8" class="empty">No implementation requirements yet.</td></tr>`}</tbody></table></div>
    <div class="addrow"><button class="btn secondary" onClick=${() => upd(n => n.impl_reqs.push({ category: "", requirement: "", assigned_to: "", due_date: "", status: "Not Started", verification: "", comments: "" }))}>+ Add Requirement</button></div></div>`;
}

/* ---------- Step 5: Attachments ---------- */
function Attachments({ m, upd }) {
  const setA = (i, k, v) => upd(n => n.attachments[i][k] = v);
  return html`<div>
    <h2>Step 5 — Attachments</h2>
    <p class="step-intro">List supporting documents: P&IDs, drawings, vendor specs, PHA reports, procedures. Paste a SharePoint/OneDrive link.</p>
    <div class="card table-card"><table><thead><tr><th>#</th><th>Description</th><th>Link / Reference</th><th></th></tr></thead>
    <tbody>${m.attachments.length ? m.attachments.map((a, i) => html`<tr class="repeater-row" key=${i}>
      <td>${i + 1}</td>
      <td><input type="text" value=${a.description || ""} onChange=${e => setA(i, "description", e.target.value)}/></td>
      <td><input type="text" value=${a.link || ""} onChange=${e => setA(i, "link", e.target.value)}/></td>
      <td><button class="del-x" onClick=${() => upd(n => n.attachments.splice(i, 1))}>×</button></td></tr>`)
      : html`<tr><td colSpan="4" class="empty">No attachments yet.</td></tr>`}</tbody></table></div>
    <div class="addrow"><button class="btn secondary" onClick=${() => upd(n => n.attachments.push({ description: "", link: "" }))}>+ Add Attachment</button></div></div>`;
}

/* ---------- Step 6: Endorsements & Approval (workflow surface) ---------- */
function decKind(d) { return d === "Approved" ? "green" : (d === "Declined" ? "earth" : "gray"); }
function Endorsements({ m, upd, save, act, editable }) {
  const state = m.workflow_state;
  const setApproval = (idx, k, v) => upd(n => n.approvals[idx][k] = v);
  const inits = m.approvals.map((a, idx) => ({ a, idx })).filter(x => x.a.kind === "initiation");
  const finals = m.approvals.filter(a => a.kind === "final");
  const reqRoles = m.required_final_roles || ["VP Operations"];
  const endorsers = m.stakeholders.filter(s => s.impacted);

  const endorse = (dept, decision) => {
    let comment = "";
    if (decision === "Declined") { comment = prompt("Reason for declining (sent back to the originator):", ""); if (comment === null) return; }
    act("endorse", { department: dept, decision, comment });
  };
  const finalDecide = (role, decision) => {
    let comment = "";
    if (decision === "Declined") { comment = prompt("Reason for declining (sent back to the originator):", ""); if (comment === null) return; }
    act("final-decision", { role, decision, comment });
  };
  const submitNow = async () => { await save(); act("submit"); };   // persist edits, then submit
  const undoEndorse = (dept) => { if (confirm("Undo this endorsement? It returns to Pending (and resets any final approvals that depended on it).")) act("clear-signoff", { kind: "endorsement", department: dept }); };
  const undoFinal = (role) => { if (confirm("Undo this approval decision? It returns to Pending.")) act("clear-signoff", { kind: "final", role: role }); };

  const decBtns = (onApprove, onDecline) => html`<div class="row-actions">
    <button class="icon-btn" style=${{ color: "var(--green)", borderColor: "#bfe0cd" }} onClick=${onApprove}>✓ Approve</button>
    <button class="icon-btn del" onClick=${onDecline}>✕ Decline</button></div>`;

  return html`<div>
    <h2>Step 6 — Endorsements & Approval</h2>
    <p class="step-intro">Submit for endorsement; each impacted department must Approve or Decline. A decline routes the MOC back to the originator. Once all endorse, the ${approvalLevel(m)} approves to implement.</p>

    ${state === "Revision Requested" && html`<div class="alert red">
      <strong>Revision requested.</strong> ${m.last_decline_by ? ("Declined by " + m.last_decline_by + ". ") : ""}${m.last_decline_reason ? ("Reason: " + m.last_decline_reason) : ""}
      Revise the change above, then resubmit (all endorsers will review again).</div>`}

    <div class="computebox"><div class="compute-grid">
      <div class="ci"><div class="k">Workflow State</div><div class="v">${state}</div></div>
      <div class="ci"><div class="k">Endorsements</div><div class="v">${m.endorsement_summary.approved}/${m.endorsement_summary.total} approved${m.endorsement_summary.declined ? (", " + m.endorsement_summary.declined + " declined") : ""}</div></div>
      <div class="ci"><div class="k">Approval Required</div><div class="v">${approvalLevel(m)}</div></div>
      <div class="ci"><div class="k">Revisions</div><div class="v">${m.revision_count || 0}</div></div>
    </div></div>

    ${(state === "Draft" || state === "Revision Requested") && html`<div style=${{ margin: "0 0 20px" }}>
      <button class="btn" disabled=${!m.can_submit} onClick=${submitNow}>${state === "Revision Requested" ? "Resubmit for Endorsement" : "Submit for Endorsement"}</button>
      ${!m.can_submit && html`<div class="mini" style=${{ marginTop: "6px" }}>Complete the Change Request, score all risks, and mark at least one impacted department first.</div>`}
    </div>`}

    <h3>Approved for Initiation</h3>
    <div class="card table-card"><table><thead><tr><th>Role</th><th>Name</th><th>Title</th><th>Initials</th><th>Date</th></tr></thead>
    <tbody>${inits.map(({ a, idx }) => html`<tr class="repeater-row" key=${idx}>
      <td><strong>${a.role}</strong></td>
      <td><input type="text" disabled=${!editable} value=${a.name || ""} onChange=${e => setApproval(idx, "name", e.target.value)}/></td>
      <td><input type="text" disabled=${!editable} value=${a.title || ""} onChange=${e => setApproval(idx, "title", e.target.value)}/></td>
      <td style=${{ width: "90px" }}><input type="text" disabled=${!editable} value=${a.initials || ""} onChange=${e => setApproval(idx, "initials", e.target.value)}/></td>
      <td style=${{ width: "130px" }}><input type="date" disabled=${!editable} value=${a.date || ""} onChange=${e => setApproval(idx, "date", e.target.value)}/></td></tr>`)}</tbody></table></div>

    <h3 style=${{ marginTop: "24px" }}>Endorsements (Impacted Departments)</h3>
    <div class="card table-card"><table><thead><tr><th>Department</th><th>Endorser</th><th>Decision</th><th>Comment</th><th></th></tr></thead>
    <tbody>${endorsers.length ? endorsers.map(s => html`<tr key=${s.idx}>
      <td><strong>${s.department}</strong></td>
      <td>${s.endorser_name || html`<span class="mini">— unassigned —</span>`}<div class="mini">${s.endorser_email || ""}</div></td>
      <td><${Badge} kind=${decKind(s.decision)}>${s.decision}<//>${s.decision_at ? html`<div class="mini">${(s.decision_at || "").replace("T", " ").slice(0, 16)} · ${s.signed_by}</div>` : ""}</td>
      <td class="mini">${s.decision_comment || ""}</td>
      <td>${s.decision !== "Pending"
        ? html`<button class="icon-btn" onClick=${() => undoEndorse(s.department)}>↺ Undo</button>`
        : (state === "Submitted for Endorsement"
            ? decBtns(() => endorse(s.department, "Approved"), () => endorse(s.department, "Declined"))
            : html`<span class="mini">—</span>`)}</td></tr>`)
      : html`<tr><td colSpan="5" class="empty">No impacted departments selected in Step 3.</td></tr>`}</tbody></table></div>
    ${state === "Submitted for Endorsement" && html`<div class="mini" style=${{ marginTop: "6px" }}>Demo: anyone can record a decision here. With Entra sign-in, each endorser acts as themselves and it's logged to their identity.</div>`}

    <h3 style=${{ marginTop: "24px" }}>Final Approval to Implement</h3>
    <div class="card table-card"><table><thead><tr><th>Role</th><th>Name</th><th>Decision</th><th>Comment</th><th></th></tr></thead>
    <tbody>${finals.map((a, i) => {
      const required = reqRoles.some(r => a.role === r || a.role.startsWith(r));
      const optional = a.role.startsWith("CEO") && approvalLevel(m) !== "CEO";
      return html`<tr key=${i} style=${optional ? { opacity: .5 } : {}}>
        <td><strong>${a.role}</strong>${a.role.startsWith("CEO") ? (approvalLevel(m) === "CEO" ? html` <${Badge} kind="high">required<//>` : html` <${Badge} kind="gray">n/a<//>`) : ""}</td>
        <td>${a.name || html`<span class="mini">—</span>`}</td>
        <td><${Badge} kind=${decKind(a.decision)}>${a.decision}<//>${a.decision_at ? html`<div class="mini">${(a.decision_at || "").replace("T", " ").slice(0, 16)} · ${a.signed_by}</div>` : ""}</td>
        <td class="mini">${a.decision_comment || ""}</td>
        <td>${a.decision !== "Pending"
          ? html`<button class="icon-btn" onClick=${() => undoFinal(a.role)}>↺ Undo</button>`
          : ((state === "Pending Final Approval" && required)
              ? decBtns(() => finalDecide(a.role, "Approved"), () => finalDecide(a.role, "Declined"))
              : html`<span class="mini">—</span>`)}</td></tr>`;
    })}</tbody></table></div>

    ${state === "Approved" && html`<div class="alert green" style=${{ marginTop: "16px" }}>Approved — ready to implement. Proceed to Closure when work is complete.</div>`}
    ${state === "Pending Final Approval" && html`<div class="alert amber" style=${{ marginTop: "16px" }}>All departments endorsed. Awaiting ${approvalLevel(m)} approval.</div>`}
    ${state === "Submitted for Endorsement" && html`<div class="alert amber" style=${{ marginTop: "16px" }}>Awaiting endorsement from ${m.awaiting.length} ${m.awaiting.length === 1 ? "person" : "people"}.</div>`}
  </div>`;
}

/* ---------- Step 7: Closure ---------- */
function Closure({ m, upd }) {
  const setC = (idx, k, v) => upd(n => { const c = n.closure_items.find(x => x.idx === idx); c[k] = v; });
  const setL = (i, k, v) => upd(n => n.lessons[i][k] = v);
  const allY = m.closure_items.every(c => c.complete);
  return html`<div>
    <h2>Step 7 — Closure</h2>
    <p class="step-intro">Verify all work is complete, capture lessons, and obtain closure sign-off. All 10 items must be Yes and a closure date entered.</p>
    <h3>Pre-Closure Verification</h3>
    <div class="card table-card"><table class="qtable"><thead><tr><th>#</th><th>Verification</th><th class="rs-cell">Complete?</th><th>Verified By</th><th>Date</th></tr></thead>
    <tbody>${m.closure_items.map(c => html`<tr key=${c.idx}>
      <td>${c.idx + 1}</td><td class="q">${c.question}</td>
      <td class="rs-cell"><select class="yn" value=${c.complete ? "Y" : "N"} onChange=${e => setC(c.idx, "complete", e.target.value === "Y")}><option value="N">No</option><option value="Y">Yes</option></select></td>
      <td><input type="text" value=${c.verified_by || ""} onChange=${e => setC(c.idx, "verified_by", e.target.value)}/></td>
      <td style=${{ width: "130px" }}><input type="date" value=${c.date || ""} onChange=${e => setC(c.idx, "date", e.target.value)}/></td></tr>`)}</tbody></table></div>
    <div class="alert ${allY ? "green" : "amber"}" style=${{ marginTop: "14px" }}>${allY ? "All items verified — ready for closure." : "Outstanding verification items remain."}</div>

    <h3 style=${{ marginTop: "24px" }}>Lessons Learned</h3>
    <div class="card table-card"><table><thead><tr><th>#</th><th>Category</th><th>Lesson / Observation</th><th>Recommended Action</th><th>Owner</th><th></th></tr></thead>
    <tbody>${m.lessons.length ? m.lessons.map((l, i) => html`<tr class="repeater-row" key=${i}>
      <td>${i + 1}</td>
      <td><input type="text" value=${l.category || ""} onChange=${e => setL(i, "category", e.target.value)}/></td>
      <td><input type="text" value=${l.lesson || ""} onChange=${e => setL(i, "lesson", e.target.value)}/></td>
      <td><input type="text" value=${l.action || ""} onChange=${e => setL(i, "action", e.target.value)}/></td>
      <td><input type="text" value=${l.owner || ""} onChange=${e => setL(i, "owner", e.target.value)}/></td>
      <td><button class="del-x" onClick=${() => upd(n => n.lessons.splice(i, 1))}>×</button></td></tr>`)
      : html`<tr><td colSpan="6" class="empty">No lessons recorded.</td></tr>`}</tbody></table></div>
    <div class="addrow"><button class="btn secondary" onClick=${() => upd(n => n.lessons.push({ category: "", lesson: "", action: "", owner: "" }))}>+ Add Lesson</button></div>

    <div class="field" style=${{ maxWidth: "260px", marginTop: "18px" }}><label>Closure Date *</label>
      <input type="date" value=${m.closure_date || ""} onChange=${e => upd(n => n.closure_date = e.target.value)}/></div></div>`;
}

/* ---------------- App / Router ---------------- */
function parseHash() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (parts[0] === "moc" && parts[1]) return { view: "wizard", id: Number(parts[1]), step: parts[2] ? Number(parts[2]) : 0 };
  if (parts[0] === "help") return { view: "help" };
  if (parts[0] === "dashboard") return { view: "dashboard" };
  if (parts[0] === "my") return { view: "my" };
  return { view: "my" };   // default landing after sign-in
}

/* ---------------- People picker ---------------- */
function PersonSelect({ email, onPick, disabled }) {
  const people = REF.people || [];
  return html`<select disabled=${disabled} value=${email || ""} onChange=${e => {
    const p = people.find(x => x.email === e.target.value);
    onPick(p ? { name: p.name, email: p.email } : { name: "", email: "" });
  }}>
    <option value="">— select person —</option>
    ${people.map(p => html`<option key=${p.email} value=${p.email}>${p.name} · ${p.department}</option>`)}
  </select>`;
}

/* ---------------- My Work (personal dashboard) ---------------- */
function MyWork({ email }) {
  const [d, setD] = useState(null);
  const load = useCallback(() => { if (email) fetch("/api/my?email=" + encodeURIComponent(email)).then(r => r.json()).then(setD); }, [email]);
  useEffect(() => { load(); }, [load]);
  if (!email) return html`<div class="wrap"><div class="loading">Pick a name in <strong>View as</strong> (top-right) to see that person's work.</div></div>`;
  if (!d) return html`<div class="wrap"><div class="loading">Loading your work…</div></div>`;
  const person = (REF.people || []).find(p => p.email === email);

  const decide = async (x, decision) => {
    let comment = "";
    if (decision === "Declined") { comment = prompt("Reason for declining (sent back to the originator):", ""); if (comment === null) return; }
    const path = x.kind === "Endorsement" ? "endorse" : "final-decision";
    const body = x.kind === "Endorsement" ? { department: x.department, decision, comment } : { role: x.role, decision, comment };
    body.actor_name = person ? person.name : ""; body.actor_email = email;
    const res = await fetch("/api/mocs/" + x.moc_id + "/" + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (res.ok) load();
  };

  return html`<div class="wrap">
    <div class="sec-head"><h2>My Work${person ? (" — " + person.name) : ""}</h2>
      <span class="mini">${person ? (person.role + " · " + person.department) : email}</span></div>

    <div class="sec-head" style=${{ marginTop: "8px" }}><h2 style=${{ fontSize: "16px" }}>Awaiting My Sign-off (${d.awaiting_me.length})</h2></div>
    <div class="card table-card">
      ${d.awaiting_me.length === 0 ? html`<div class="empty">Nothing is waiting on you right now.</div>` : html`
      <table><thead><tr><th>MOC</th><th>Type</th><th>What's needed</th><th></th></tr></thead>
      <tbody>${d.awaiting_me.map((x, i) => html`<tr key=${i}>
        <td><strong>${x.moc}</strong></td>
        <td><${Badge} kind=${x.kind === "Final Approval" ? "high" : "cobalt"}>${x.kind}<//></td>
        <td>${x.what}</td>
        <td><div class="row-actions">
          <button class="icon-btn" style=${{ color: "var(--green)", borderColor: "#bfe0cd" }} onClick=${() => decide(x, "Approved")}>✓ Approve</button>
          <button class="icon-btn del" onClick=${() => decide(x, "Declined")}>✕ Decline</button>
          <button class="icon-btn" onClick=${() => location.hash = "#/moc/" + x.moc_id + "/5"}>Open</button>
        </div></td></tr>`)}</tbody></table>`}
    </div>

    <div class="sec-head"><h2 style=${{ fontSize: "16px" }}>My MOCs (${d.my_mocs.length})</h2></div>
    <div class="card table-card">
      ${d.my_mocs.length === 0 ? html`<div class="empty">You haven't initiated or been assigned to any MOCs.</div>` : html`
      <table><thead><tr><th>Change #</th><th>Change Name</th><th>My Role</th><th>Workflow State</th><th></th></tr></thead>
      <tbody>${d.my_mocs.map(m => html`<tr key=${m.id}>
        <td><strong>${m.change_number}</strong></td><td>${m.change_name || "(untitled)"}</td>
        <td>${m.my_roles.map(r => html`<${Badge} kind="gray">${r}<//> `)}</td>
        <td><${Badge} kind=${stateKind(m.workflow_state)}>${m.workflow_state}<//></td>
        <td><button class="icon-btn" onClick=${() => location.hash = "#/moc/" + m.id + "/0"}>Open</button></td></tr>`)}</tbody></table>`}
    </div>

    <div class="sec-head"><h2 style=${{ fontSize: "16px" }}>My Actions (${d.my_actions.length})</h2></div>
    <div class="card table-card">
      ${d.my_actions.length === 0 ? html`<div class="empty">No action items assigned to you.</div>` : html`
      <table><thead><tr><th>MOC</th><th>Type</th><th>Item</th><th>Due</th><th>Status</th><th></th></tr></thead>
      <tbody>${d.my_actions.map((a, i) => html`<tr key=${i}>
        <td><strong>${a.moc}</strong></td>
        <td><${Badge} kind=${a.kind === "Action" ? "cobalt" : "gray"}>${a.kind}<//></td>
        <td>${a.item}</td>
        <td class=${a.days_late ? "tag-late" : ""}>${a.due || "—"}${a.days_late ? (" · " + a.days_late + "d late") : ""}</td>
        <td><${Badge} kind=${a.status === "Complete" ? "green" : (a.status === "Blocked" ? "earth" : "gray")}>${a.status}<//></td>
        <td><button class="icon-btn" onClick=${() => location.hash = "#/moc/" + a.moc_id + "/3"}>Open</button></td></tr>`)}</tbody></table>`}
    </div>
  </div>`;
}

/* ---------------- How to Use / PSM alignment ---------------- */
const PSM_ROWS = [
  ["(l)(1) Manage changes except “replacement in kind”", "Step 1 Checklist screens whether an OMOC is required and flags Emergency/Temporary changes."],
  ["(l)(2)(i) Technical basis for the change", "Step 2 Change Request — Description & Justification."],
  ["(l)(2)(ii) Impact on safety and health", "Step 3 Risk & Stakeholders — Severity × Likelihood across safety/health/environmental, compliance, technical, organizational, and financial categories; PHA level (What-If / HAZOP) auto-flagged."],
  ["(l)(2)(iii) Modifications to operating procedures", "Step 4 action items to revise procedures + Step 7 closure verification that affected procedures were updated."],
  ["(l)(2)(iv) Necessary time period for the change", "Date Requested, action-item due dates, and the Temporary reversion/reevaluation concept."],
  ["(l)(2)(v) Authorization requirements", "Step 6 risk-based routing (VP Operations / CEO) + impacted-department endorsement workflow; authorization is enforced before the change can be closed/implemented."],
  ["(l)(3) Affected employees informed & trained before start-up", "Step 7 closure item “required training completed and documented,” plus training action items in Step 4."],
  ["(l)(4) Update process safety information (PSI)", "Step 7 closure item “affected P&IDs, drawings, and technical documents updated.”"],
  ["(l)(5) Update operating procedures", "Step 7 closure item “affected operating procedures updated and approved.”"],
];
function Help() {
  const step = (n, t, d) => html`<div style=${{ display: "flex", gap: "12px", padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
    <div class="marker" style=${{ width: "26px", height: "26px", borderRadius: "50%", background: "var(--cobalt)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, flex: "none" }}>${n}</div>
    <div><strong>${t}</strong><div class="mini">${d}</div></div></div>`;
  return html`<div class="wrap">
    <div class="sec-head"><h2>How to Use This Tool</h2><a class="navlink" style=${{ color: "var(--cobalt)" }} onClick=${() => location.hash = "#/dashboard"}>← Dashboard</a></div>

    <div class="panel" style=${{ marginBottom: "20px" }}>
      <h3>What this is</h3>
      <p>A staged workflow and dashboard for Fervo's Operations Management of Change (OMOC) process. The <strong>dashboard</strong> tracks active and completed MOCs, late action items, and who still owes a sign-off. Each MOC is completed as a <strong>7-step wizard</strong>, and moves through an <strong>approval workflow</strong> before it can be implemented and closed.</p>

      <h3 style=${{ marginTop: "18px" }}>The 7 steps</h3>
      ${step(1, "Checklist", "Screen the change — is an OMOC required, and is it Emergency or Temporary?")}
      ${step(2, "Change Request", "Describe and justify the change. Priority and flags calculate automatically.")}
      ${step(3, "Risk & Stakeholders", "Score Severity × Likelihood for each risk; approval level, PHA, and risk level calculate from the highest score. Mark impacted departments — they become the endorsers.")}
      ${step(4, "Actions & Implementation", "List the action items and implementation requirements, with owners and due dates.")}
      ${step(5, "Attachments", "Link supporting documents — P&IDs, drawings, vendor specs, PHA reports.")}
      ${step(6, "Endorsements & Approval", "Submit for endorsement; each impacted department Approves or Declines. A decline routes back to the originator to revise and resubmit. Once all endorse, the VP Operations (or CEO, for higher risk) gives final approval.")}
      ${step(7, "Closure", "Verify all work, training, procedure and drawing updates are complete; capture lessons learned; sign off to close.")}

      <h3 style=${{ marginTop: "18px" }}>Approval workflow</h3>
      <p class="mini">Draft → Submitted for Endorsement → (Revision Requested, if any department declines) → Pending Final Approval → Approved → Closed. The MOC cannot reach final approval until every impacted department has endorsed, and cannot close until it is approved and all closure items are verified.</p>
    </div>

    <div class="panel">
      <h3>Alignment with OSHA PSM — 29 CFR 1910.119(l), Management of Change</h3>
      <p class="mini">This tool is designed to support and document the Management of Change element of the OSHA Process Safety Management standard. Each requirement maps to where the tool addresses it:</p>
      <div class="card table-card" style=${{ marginTop: "10px" }}>
        <table><thead><tr><th style=${{ width: "42%" }}>29 CFR 1910.119(l) requirement</th><th>How this tool supports it</th></tr></thead>
        <tbody>${PSM_ROWS.map((r, i) => html`<tr key=${i}><td><strong>${r[0]}</strong></td><td>${r[1]}</td></tr>`)}</tbody></table>
      </div>
      <div class="alert amber" style=${{ marginTop: "16px" }}>
        <strong>Scope &amp; disclaimer.</strong> The tool documents, routes, and tracks the MOC — it does not itself deliver training or update process safety information / operating procedures; those happen in your systems, and the tool records that they were addressed. It is decision-support, not a guarantee of regulatory compliance — confirm against your site PSM program. This prototype records authorizations but does not yet enforce them by verified identity; identity-based sign-off and a tamper-evident audit trail come with the Entra ID / Azure deployment.
      </div>
    </div>
  </div>`;
}
function App() {
  const [route, setRoute] = useState(parseHash());
  const [ready, setReady] = useState(false);
  const [userEmail, setUserEmail] = useState(localStorage.getItem("omoc_user") || "");
  useEffect(() => {
    API.reference().then(r => { REF = r; setReady(true); });
    const onHash = () => setRoute(parseHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const pickUser = e => { setUserEmail(e.target.value); localStorage.setItem("omoc_user", e.target.value); };
  const people = ready ? (REF.people || []) : [];
  const currentUser = people.find(p => p.email === userEmail) || { name: "", email: userEmail };
  return html`
    <div class="topbar">
      <img src="/static/fervo-logo-white.png" alt="Fervo Energy"/>
      <div><div class="title">Operations Management of Change</div><div class="sub">OMOC Workflow & Tracking</div></div>
      <div class="spacer"></div>
      <div class="viewas" title="Stand-in for Entra ID sign-in — pick who you're acting as">
        <span>View as</span>
        <select value=${userEmail} onChange=${pickUser}>
          <option value="">— select —</option>
          ${people.map(p => html`<option key=${p.email} value=${p.email}>${p.name}</option>`)}
        </select>
      </div>
      <a class="navlink" onClick=${() => location.hash = "#/my"}>My Work</a>
      <a class="navlink" onClick=${() => location.hash = "#/dashboard"}>Dashboard</a>
      <a class="navlink" onClick=${() => location.hash = "#/help"}>How to Use</a>
    </div>
    ${!ready ? html`<div class="wrap"><div class="loading">Loading…</div></div>`
      : (route.view === "my" ? html`<${MyWork} key=${userEmail} email=${userEmail}/>`
        : route.view === "help" ? html`<${Help}/>`
        : route.view === "wizard" ? html`<${Wizard} key=${route.id + "-" + route.step} id=${route.id} step=${route.step} user=${currentUser}/>`
        : html`<${Dashboard}/>`)}
    <div class="footer-note">Fervo Energy — OMOC. FastAPI + SQLite + React. “View as” is a stand-in for Entra ID sign-in (prototype).</div>`;
}
ReactDOM.createRoot(document.getElementById("root")).render(html`<${App}/>`);
