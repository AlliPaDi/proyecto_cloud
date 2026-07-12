// ── Vistas de Slices: listar, detalle, aprobar/rechazar, eliminar ──
// Endpoints reales del Slice Manager:
//   GET  /slices/            → {slices:[{id,name,status,vms_count,created_at}]}
//   GET  /slices/{id}        → {id,name,status,vlan_slice,vms:[{...,vnc_url,interfaces}]}
//   POST /slices/{id}/approve  (SLICE_ADMIN)
//   POST /slices/{id}/reject   (SLICE_ADMIN)
//   DELETE /slices/{id}

// ── STUDENT: mis slices ───────────────────────────────────────
async function renderMySlices() {
  const seq = beginRender();
  const content = document.getElementById('content');
  content.innerHTML = `<div class="text-muted">Cargando...</div>`;
  try {
    const { slices } = await api('GET', '/slices/');
    if (isStale(seq)) return;
    if (slices.length === 0) {
      content.innerHTML = `<div class="card"><div class="empty-state"><div class="empty-icon">🗂️</div><p>No tienes slices. <a href="#" onclick="navigate('new-slice')">Solicita uno.</a></p></div></div>`;
      return;
    }
    content.innerHTML = `<div class="card">
      <div class="card-title">Mis Slices <button class="btn btn-primary btn-sm" onclick="navigate('new-slice')">+ Solicitar Slice</button></div>
      <div class="table-wrap"><table>
        <thead><tr><th>ID</th><th>Nombre</th><th>VMs</th><th>Estado</th><th>Acciones</th></tr></thead>
        <tbody>${slices.map(s => `
          <tr>
            <td class="text-muted">#${s.id}</td>
            <td><strong>${esc(s.name)}</strong></td>
            <td class="text-muted">${s.vms_count}</td>
            <td>${badge(s.status)}</td>
            <td style="display:flex;gap:6px;flex-wrap:wrap">
              <button class="btn btn-ghost btn-sm" onclick="viewSliceDetail(${s.id})">Ver detalle</button>
              <button class="btn btn-danger btn-sm" onclick="deleteSlice(${s.id})">Eliminar</button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table></div>
    </div>`;
  } catch (e) {
    if (isStale(seq)) return;
    content.innerHTML = `<div class="card"><p class="error-msg">${esc(e.message)}</p></div>`;
  }
}

// ── SLICE_ADMIN: pendientes de aprobación ─────────────────────
async function renderPending() {
  const seq = beginRender();
  const content = document.getElementById('content');
  content.innerHTML = `<div class="text-muted">Cargando...</div>`;
  try {
    const { slices } = await api('GET', '/slices/');
    if (isStale(seq)) return;
    const pending = slices.filter(s => s.status === 'PENDING_APPROVAL');

    if (pending.length === 0) {
      content.innerHTML = `<div class="card"><div class="empty-state"><div class="empty-icon">✅</div><p>No hay solicitudes pendientes.</p></div></div>`;
      return;
    }

    content.innerHTML = `<div class="card">
      <div class="card-title">Solicitudes pendientes de aprobación</div>
      <div class="table-wrap"><table>
        <thead><tr><th>ID</th><th>Nombre</th><th>VMs</th><th>Estado</th><th>Acciones</th></tr></thead>
        <tbody>${pending.map(s => `
          <tr>
            <td class="text-muted">#${s.id}</td>
            <td><strong>${esc(s.name)}</strong></td>
            <td class="text-muted">${s.vms_count}</td>
            <td>${badge(s.status)}</td>
            <td style="display:flex;gap:6px;flex-wrap:wrap">
              <button class="btn btn-ghost btn-sm" onclick="viewSliceDetail(${s.id})">Ver</button>
              <button class="btn btn-success btn-sm" onclick="approveSlice(${s.id})">Aprobar</button>
              <button class="btn btn-danger btn-sm"  onclick="rejectSlice(${s.id})">Rechazar</button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table></div>
    </div>`;
  } catch (e) {
    if (isStale(seq)) return;
    content.innerHTML = `<div class="card"><p class="error-msg">${esc(e.message)}</p></div>`;
  }
}

// ── ADMIN: todos los slices ───────────────────────────────────
async function renderAllSlices() {
  const seq = beginRender();
  const content = document.getElementById('content');
  content.innerHTML = `<div class="text-muted">Cargando...</div>`;
  try {
    const { slices } = await api('GET', '/slices/');
    if (isStale(seq)) return;

    const actions = state.user.role === 'SLICE_ADMIN'
      ? s => `
          <button class="btn btn-ghost btn-sm" onclick="viewSliceDetail(${s.id})">Ver</button>
          ${s.status === 'PENDING_APPROVAL'
            ? `<button class="btn btn-success btn-sm" onclick="approveSlice(${s.id})">Aprobar</button>
               <button class="btn btn-danger  btn-sm" onclick="rejectSlice(${s.id})">Rechazar</button>`
            : ''}
          <button class="btn btn-danger btn-sm" onclick="deleteSlice(${s.id})">Eliminar</button>`
      : s => `
          <button class="btn btn-ghost btn-sm" onclick="viewSliceDetail(${s.id})">Ver</button>
          <button class="btn btn-ghost  btn-sm" onclick="viewNetDetail(${s.id})">Red</button>
          <button class="btn btn-danger btn-sm" onclick="deleteSlice(${s.id})">Eliminar</button>`;

    content.innerHTML = slices.length === 0
      ? `<div class="card"><div class="empty-state"><div class="empty-icon">📭</div><p>No hay slices en el sistema.</p></div></div>`
      : `<div class="card">
          <div class="card-title">Todos los Slices</div>
          <div class="table-wrap"><table>
            <thead><tr><th>ID</th><th>Nombre</th><th>Estado</th><th>VMs</th><th>Creado</th><th>Acciones</th></tr></thead>
            <tbody>${slices.map(s => `
              <tr>
                <td class="text-muted">#${s.id}</td>
                <td><strong>${esc(s.name)}</strong></td>
                <td>${badge(s.status)}</td>
                <td class="text-muted">${s.vms_count}</td>
                <td class="text-muted text-sm">${s.created_at ? new Date(s.created_at).toLocaleString() : '—'}</td>
                <td style="display:flex;gap:6px;flex-wrap:wrap">${actions(s)}</td>
              </tr>`).join('')}
            </tbody>
          </table></div>
        </div>`;
  } catch (e) {
    if (isStale(seq)) return;
    content.innerHTML = `<div class="card"><p class="error-msg">${esc(e.message)}</p></div>`;
  }
}

// ── Detalle de slice (modal) ──────────────────────────────────
// El backend ya no devuelve topología ni IPs en el detalle;
// las interfaces traen: interface_name, tap_name, vlan_inner, bridge_name.
async function viewSliceDetail(id) {
  try {
    const s = await api('GET', `/slices/${id}`);
    const vmsHTML = s.vms.map(vm => `
      <div style="margin-bottom:12px;padding:12px;background:var(--bg);border:1px solid var(--border);border-radius:6px">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
          <strong style="font-size:13px">${esc(vm.name)}</strong>
          ${badge(vm.status)}
        </div>
        <div style="font-size:12px;color:var(--text-muted);display:flex;gap:16px;margin-bottom:8px;flex-wrap:wrap">
          ${vm.worker_id  ? `<span>Worker: ${vm.worker_id}</span>`   : ''}
          ${vm.vnc_port   ? `<span>VNC: ${vm.vnc_port}</span>`       : ''}
          ${vm.process_id ? `<span>PID: ${vm.process_id}</span>`     : ''}
          ${vm.vnc_url    ? `<a href="${esc(vm.vnc_url)}" target="_blank" rel="noopener" style="color:var(--primary)">Abrir consola VNC ↗</a>` : ''}
        </div>
        ${vm.interfaces.length ? `
          <div class="table-wrap"><table>
            <thead><tr><th>Interfaz</th><th>TAP</th><th>VLAN inner</th><th>Bridge</th></tr></thead>
            <tbody>${vm.interfaces.map(i => `
              <tr>
                <td class="mono">${esc(i.interface_name) || '—'}</td>
                <td class="mono text-muted">${esc(i.tap_name) || '—'}</td>
                <td class="mono text-muted">${i.vlan_inner != null ? i.vlan_inner : '—'}</td>
                <td class="mono text-muted">${esc(i.bridge_name) || '—'}</td>
              </tr>`).join('')}
            </tbody>
          </table></div>` : '<p class="text-muted text-sm">Sin interfaces asignadas aún.</p>'}
      </div>`).join('') || '<p class="text-muted text-sm">No hay VMs.</p>';

    openModal(`Slice #${s.id} — ${esc(s.name)}`, `
      <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">
        ${badge(s.status)}
        <span class="text-muted text-sm">ID: ${s.id}</span>
        ${s.vlan_slice ? `<span class="text-muted text-sm">VLAN-Slice: ${s.vlan_slice}</span>` : ''}
      </div>
      <div class="card-title" style="margin-bottom:12px">Máquinas Virtuales</div>
      ${vmsHTML}
    `);
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ── Acciones ──────────────────────────────────────────────────
async function approveSlice(id) {
  try {
    const res = await api('POST', `/slices/${id}/approve`);
    toast(res.message || `Slice #${id} aprobado`, 'success');
    navigate(state.view);
  } catch (e) { toast(e.message, 'error'); }
}

async function rejectSlice(id) {
  if (!confirm(`¿Rechazar slice #${id}?`)) return;
  try {
    await api('POST', `/slices/${id}/reject`);
    toast(`Slice #${id} rechazado`, 'info');
    navigate(state.view);
  } catch (e) { toast(e.message, 'error'); }
}

async function deleteSlice(id) {
  if (!confirm(`¿Eliminar slice #${id}? Se apagarán sus VMs y se liberará la red.`)) return;
  try {
    await api('DELETE', `/slices/${id}`);
    toast('Slice eliminado', 'success');
    navigate(state.view);
  } catch (e) {
    toast(e.message, 'error');
  }
}
