/* Chore Roster SPA — vanilla JS, talks to the Django REST API. */
const API = '/api';

const state = { view: 'dashboard', dash: null, chores: [], members: [], completions: [], stats: null, modal: null };

/* ---------- api helpers ---------- */
const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) throw new Error((await res.text()).slice(0, 200));
  return res.status === 204 ? null : res.json();
}
const get = p => api(p);
const post = (p, body) => api(p, { method: 'POST', body });
const patch = (p, body) => api(p, { method: 'PATCH', body });
const del = p => api(p, { method: 'DELETE' });

/* ---------- utils ---------- */
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const avatar = (name, color, initials) =>
  `<div class="avatar" style="background:${esc(color || '#5b8cff')}" title="${esc(name || '')}">${esc(initials || '?')}</div>`;
const dueLabel = c => c.days_until_due < 0 ? `${-c.days_until_due}d overdue`
  : c.days_until_due === 0 ? 'due today'
  : c.days_until_due === 1 ? 'due tomorrow' : `in ${c.days_until_due}d`;
const diffBars = n => `<span class="diff">${[1,2,3,4,5].map(i => `<i class="${i <= n ? 'on' : ''}"></i>`).join('')}</span>`;
const when = iso => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

function toast(msg) {
  document.querySelector('.toast')?.remove();
  const el = Object.assign(document.createElement('div'), { className: 'toast', textContent: msg });
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2600);
}

/* ---------- data ---------- */
async function refresh() {
  const [dash, chores, members, completions, stats] = await Promise.all([
    get('/dashboard/'), get('/chores/'), get('/members/'), get('/completions/?limit=60'), get('/stats/'),
  ]);
  Object.assign(state, {
    dash, stats,
    chores: chores.results || chores,
    members: members.results || members,
    completions: completions.results || completions,
  });
  render();
}

/* ---------- views ---------- */
function choreCard(c) {
  return `<div class="card">
    ${avatar(c.assigned_to_name, c.assigned_to_color, (c.assigned_to_name || '?').split(' ').map(w => w[0]).slice(0,2).join('').toUpperCase())}
    <div class="body">
      <div class="title">${esc(c.name)}
        <span class="pill ${c.status}">${dueLabel(c)}</span>
        <span class="pill pts">+${c.points} pts</span>
      </div>
      <div class="meta">
        <span>${esc(c.assigned_to_name || 'unassigned')}</span>
        <span>· ${esc(c.recurrence_display)}</span>
        <span>· ${diffBars(c.difficulty)}</span>
        ${c.description ? `<span>· ${esc(c.description)}</span>` : ''}
      </div>
    </div>
    <div class="actions">
      <button class="btn sm" data-done="${c.id}">Done</button>
      <button class="btn ghost sm" data-snooze="${c.id}">+1d</button>
      <button class="btn ghost sm" data-edit="${c.id}">Edit</button>
    </div>
  </div>`;
}

function viewDashboard() {
  const d = state.dash; if (!d) return '';
  const s = d.stats;
  const bucket = (key, label) => {
    const items = d.buckets[key];
    if (!items.length) return '';
    return `<h2>${label} · ${items.length}</h2>${items.map(choreCard).join('')}`;
  };
  const anyChores = Object.values(d.buckets).some(b => b.length);
  return `
  <div class="page-head">
    <div><h1>Dashboard</h1><div class="sub">Who owes the household what, right now.</div></div>
    <button class="btn" data-modal="chore">+ New chore</button>
  </div>
  <div class="stats">
    <div class="stat ${s.overdue ? 'alert' : ''}"><div class="n">${s.overdue}</div><div class="l">Overdue</div></div>
    <div class="stat"><div class="n">${s.due_today}</div><div class="l">Due today</div></div>
    <div class="stat"><div class="n">${s.total_chores}</div><div class="l">Active chores</div></div>
    <div class="stat"><div class="n">${s.completed_this_week}</div><div class="l">Done this week</div></div>
    <div class="stat"><div class="n">${s.points_this_week}</div><div class="l">Points this week</div></div>
  </div>
  ${anyChores ? bucket('overdue','⚠️ Overdue') + bucket('today','Due today') + bucket('soon','Next 3 days') + bucket('upcoming','Later')
    : `<div class="empty" style="margin-top:22px">No active chores yet. Add members, then create your first chore.</div>`}
  <div class="grid2" style="margin-top:28px">
    <div><h2 style="margin-top:0">Leaderboard</h2><div class="panel">${leaderboardHTML(d.leaderboard)}</div></div>
    <div><h2 style="margin-top:0">Recent activity</h2><div class="panel">${
      d.recent.length ? d.recent.map(r => `<div class="bar-row"><div class="nm">${esc(r.member_name || '—')}</div>
        <div style="flex:1;font-size:13px">${esc(r.chore_name)}${r.was_late ? ' <span class="pill overdue">late</span>' : ''}</div>
        <div class="v">${when(r.completed_at)}</div></div>`).join('')
      : '<div class="sub">Nothing completed yet.</div>'}</div></div>
  </div>`;
}

function leaderboardHTML(list) {
  if (!list.length) return '<div class="sub">No members yet.</div>';
  const max = Math.max(...list.map(m => m.points), 1);
  return list.map((m, i) => `<div class="bar-row">
    <div class="rank ${i < 3 ? 'g' + (i + 1) : ''}">${i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}</div>
    <div class="nm">${esc(m.name)}</div>
    <div class="bar"><i style="width:${(m.points / max) * 100}%;background:${esc(m.color)}"></i></div>
    <div class="v">${m.points} pts</div></div>`).join('');
}

function viewChores() {
  return `<div class="page-head">
    <div><h1>Chores</h1><div class="sub">${state.chores.length} total · click Edit to change recurrence or owner</div></div>
    <button class="btn" data-modal="chore">+ New chore</button></div>
  ${state.chores.length ? state.chores.map(choreCard).join('') : '<div class="empty">No chores yet.</div>'}`;
}

function viewMembers() {
  return `<div class="page-head">
    <div><h1>Members</h1><div class="sub">Chores rotate through active members in this order.</div></div>
    <button class="btn" data-modal="member">+ Add member</button></div>
  ${state.members.length ? `<table><tr><th></th><th>Name</th><th>Email</th><th>Open chores</th><th>Done</th><th>Points</th><th></th></tr>
    ${state.members.map(m => `<tr>
      <td>${avatar(m.name, m.color, m.initials)}</td>
      <td><strong>${esc(m.name)}</strong>${m.is_active ? '' : ' <span class="pill">inactive</span>'}</td>
      <td class="sub">${esc(m.email || '—')}</td>
      <td>${m.open_chore_count}</td><td>${m.completion_count}</td><td>${m.points}</td>
      <td style="text-align:right"><button class="btn danger sm" data-delmember="${m.id}">Remove</button></td>
    </tr>`).join('')}</table>` : '<div class="empty">No household members yet.</div>'}`;
}

function viewHistory() {
  return `<div class="page-head"><div><h1>History</h1><div class="sub">Every completed chore, newest first.</div></div></div>
  ${state.completions.length ? `<table><tr><th>Chore</th><th>By</th><th>When</th><th>Points</th><th>Note</th></tr>
    ${state.completions.map(c => `<tr><td>${esc(c.chore_name)}${c.was_late ? ' <span class="pill overdue">late</span>' : ''}</td>
      <td>${esc(c.member_name || '—')}</td><td class="sub">${when(c.completed_at)}</td>
      <td>+${c.points_awarded}</td><td class="sub">${esc(c.note || '')}</td></tr>`).join('')}</table>`
    : '<div class="empty">Nothing completed yet.</div>'}`;
}

function viewStats() {
  const s = state.stats; if (!s) return '';
  const maxP = Math.max(...s.by_member.map(m => m.points), 1);
  const maxC = Math.max(...s.by_chore.map(c => c.count), 1);
  return `<div class="page-head"><div><h1>Stats</h1><div class="sub">Is the workload actually fair?</div></div></div>
  <div class="stats"><div class="stat"><div class="n">${s.late_rate}%</div><div class="l">Completed late</div></div></div>
  <div class="grid2" style="margin-top:22px">
    <div><h2 style="margin-top:0">Points by member</h2><div class="panel">${
      s.by_member.length ? s.by_member.map(m => `<div class="bar-row"><div class="nm">${esc(m.name)}</div>
        <div class="bar"><i style="width:${(m.points / maxP) * 100}%;background:${esc(m.color)}"></i></div>
        <div class="v">${m.points} (${m.count})</div></div>`).join('') : '<div class="sub">No data yet.</div>'}</div></div>
    <div><h2 style="margin-top:0">Most-completed chores</h2><div class="panel">${
      s.by_chore.length ? s.by_chore.map(c => `<div class="bar-row"><div class="nm">${esc(c.name)}</div>
        <div class="bar"><i style="width:${(c.count / maxC) * 100}%;background:var(--acc)"></i></div>
        <div class="v">${c.count}×</div></div>`).join('') : '<div class="sub">No data yet.</div>'}</div></div>
  </div>`;
}

/* ---------- modals ---------- */
function modalHTML() {
  const m = state.modal; if (!m) return '';
  if (m.type === 'member') return wrap('Add household member', `
    <div class="field"><label>Name</label><input id="f-name" placeholder="e.g. Ana" autofocus></div>
    <div class="field"><label>Email (optional)</label><input id="f-email" type="email" placeholder="ana@home.local"></div>`);
  const c = m.data || {};
  const opts = state.members.map(x => `<option value="${x.id}" ${c.assigned_to === x.id ? 'selected' : ''}>${esc(x.name)}</option>`).join('');
  return wrap(c.id ? 'Edit chore' : 'New chore', `
    <div class="field"><label>Name</label><input id="f-name" value="${esc(c.name || '')}" placeholder="e.g. Take out trash" autofocus></div>
    <div class="field"><label>Description</label><textarea id="f-desc" rows="2" placeholder="Optional details">${esc(c.description || '')}</textarea></div>
    <div class="row">
      <div class="field"><label>Recurrence</label><select id="f-rec">${
        [['daily','Daily'],['weekly','Weekly'],['biweekly','Every 2 weeks'],['monthly','Monthly']]
        .map(([v,l]) => `<option value="${v}" ${c.recurrence === v ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
      <div class="field"><label>Difficulty (1-5)</label><input id="f-diff" type="number" min="1" max="5" value="${c.difficulty || 2}"></div>
    </div>
    <div class="row">
      <div class="field"><label>Assign to</label><select id="f-member"><option value="">— unassigned —</option>${opts}</select></div>
      <div class="field"><label>Due date</label><input id="f-due" type="date" value="${c.due_date || new Date().toISOString().slice(0,10)}"></div>
    </div>
    <div class="field"><label>Assignment mode</label><select id="f-mode">
      <option value="rotate" ${c.assignment_mode === 'keep' ? '' : 'selected'}>Rotate to next member</option>
      <option value="keep" ${c.assignment_mode === 'keep' ? 'selected' : ''}>Always same member</option></select></div>`,
    c.id ? `<button class="btn danger" data-delchore="${c.id}">Delete</button>` : '');
}
function wrap(title, body, extra = '') {
  return `<div class="overlay" data-overlay><div class="modal"><h3>${title}</h3>${body}
    <div class="modal-foot">${extra}<button class="btn ghost" data-close>Cancel</button><button class="btn" data-save>Save</button></div></div></div>`;
}

/* ---------- render + events ---------- */
const VIEWS = { dashboard: viewDashboard, chores: viewChores, members: viewMembers, history: viewHistory, stats: viewStats };
const NAV = [['dashboard','🏠','Dashboard'],['chores','🧹','Chores'],['members','👥','Members'],['history','🕓','History'],['stats','📊','Stats']];

function render() {
  document.getElementById('root').innerHTML = `<div class="shell">
    <aside class="sidebar">
      <div class="brand"><span>🧹</span> Chore Roster</div>
      ${NAV.map(([k, i, l]) => `<button class="nav ${state.view === k ? 'active' : ''}" data-view="${k}"><span class="ico">${i}</span>${l}</button>`).join('')}
      <div class="sidebar-foot">Django REST API<br>+ vanilla JS frontend<br><a href="/api/" target="_blank">Browse the API →</a></div>
    </aside>
    <main class="content">${VIEWS[state.view]()}</main>
  </div>${modalHTML()}`;
}

document.addEventListener('click', async e => {
  const t = e.target.closest('[data-view],[data-done],[data-snooze],[data-edit],[data-modal],[data-close],[data-save],[data-delmember],[data-delchore],[data-overlay]');
  if (!t) return;
  const d = t.dataset;
  try {
    if (d.view) { state.view = d.view; render(); }
    else if (d.done) { const r = await post(`/chores/${d.done}/done/`, {}); toast(`Done! Next up: ${r.chore.assigned_to_name || 'nobody'}`); await refresh(); }
    else if (d.snooze) { await post(`/chores/${d.snooze}/snooze/`, { days: 1 }); toast('Snoozed 1 day'); await refresh(); }
    else if (d.edit) { state.modal = { type: 'chore', data: state.chores.find(c => c.id == d.edit) }; render(); }
    else if (d.modal) { state.modal = { type: d.modal }; render(); }
    else if (d.close !== undefined || (d.overlay !== undefined && e.target === t)) { state.modal = null; render(); }
    else if (d.delmember) { if (confirm('Remove this member?')) { await del(`/members/${d.delmember}/`); toast('Member removed'); await refresh(); } }
    else if (d.delchore) { if (confirm('Delete this chore?')) { await del(`/chores/${d.delchore}/`); state.modal = null; toast('Chore deleted'); await refresh(); } }
    else if (d.save !== undefined) await save();
  } catch (err) { alert('Error: ' + err.message); }
});
document.addEventListener('keydown', e => { if (e.key === 'Escape' && state.modal) { state.modal = null; render(); } });

async function save() {
  const v = id => document.getElementById(id)?.value.trim() ?? '';
  if (state.modal.type === 'member') {
    if (!v('f-name')) return alert('Name is required.');
    await post('/members/', { name: v('f-name'), email: v('f-email') });
    toast('Member added');
  } else {
    if (!v('f-name')) return alert('Name is required.');
    const body = {
      name: v('f-name'), description: v('f-desc'), recurrence: v('f-rec'),
      difficulty: +v('f-diff') || 2, due_date: v('f-due'),
      assigned_to: v('f-member') ? +v('f-member') : null,
      assignment_mode: v('f-mode'), is_active: true,
    };
    const id = state.modal.data?.id;
    id ? await patch(`/chores/${id}/`, body) : await post('/chores/', body);
    toast(id ? 'Chore updated' : 'Chore created');
  }
  state.modal = null;
  await refresh();
}

refresh().catch(err => { document.getElementById('root').innerHTML = `<div class="empty" style="margin:40px">Could not reach the API: ${esc(err.message)}</div>`; });
