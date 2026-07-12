// ── Flavors: catálogo + creación (admins) ─────────────────────
// GET  /flavors/  → lista (los STUDENT solo ven flavors allowed_role=STUDENT)
// POST /flavors/  → crear (SLICE_ADMIN / SYSTEM_ADMIN)

async function renderFlavors() {
  const seq = beginRender();
  const content = document.getElementById('content');
  content.innerHTML = `<div class="text-muted">Cargando...</div>`;
  try {
    const flavors = await api('GET', '/flavors/');
    if (isStale(seq)) return;
    const isAdmin = ['SLICE_ADMIN', 'SYSTEM_ADMIN'].includes(state.user.role);

    const tableHTML = flavors.length === 0
      ? `<div class="empty-state"><div class="empty-icon">🍦</div><p>No hay flavors registrados.</p></div>`
      : `<div class="table-wrap"><table>
          <thead><tr><th>ID</th><th>Nombre</th><th>RAM</th><th>vCPU</th><th>Disco</th>${isAdmin ? '<th>Rol permitido</th>' : ''}</tr></thead>
          <tbody>${flavors.map(f => `
            <tr>
              <td class="text-muted">#${f.id}</td>
              <td><strong>${esc(f.name)}</strong></td>
              <td class="mono">${f.ram} MB</td>
              <td class="mono">${f.vcpu}</td>
              <td class="mono">${f.disk} GB</td>
              ${isAdmin ? `<td>${badge(f.allowed_role)}</td>` : ''}
            </tr>`).join('')}
          </tbody>
        </table></div>`;

    const createHTML = isAdmin ? `
      <div class="card">
        <div class="card-title">Crear flavor</div>
        <div class="field-row">
          <div class="field"><label>Nombre</label><input type="text" id="nf-name" placeholder="ej. small" /></div>
          <div class="field"><label>RAM (MB)</label><input type="number" id="nf-ram" value="1024" min="128" step="128" /></div>
        </div>
        <div class="field-row">
          <div class="field"><label>vCPUs</label><input type="number" id="nf-vcpu" value="1" min="1" /></div>
          <div class="field"><label>Disco (GB)</label><input type="number" id="nf-disk" value="10" min="1" /></div>
        </div>
        <div class="field"><label>Rol permitido</label>
          <select id="nf-role">
            <option value="STUDENT">STUDENT — visible para todos</option>
            <option value="SLICE_ADMIN">SLICE_ADMIN — solo administradores</option>
          </select>
        </div>
        <button class="btn btn-primary" onclick="createFlavor()">Crear flavor</button>
      </div>` : '';

    content.innerHTML = `
      <div class="card" style="margin-bottom:16px">
        <div class="card-title">
          Flavors disponibles
          <span class="text-muted text-sm" style="font-weight:400;margin-left:8px">${flavors.length} en total</span>
        </div>
        ${tableHTML}
      </div>
      ${createHTML}`;
  } catch (e) {
    if (isStale(seq)) return;
    content.innerHTML = `<div class="card"><p class="error-msg">${esc(e.message)}</p></div>`;
  }
}

async function createFlavor() {
  const name = document.getElementById('nf-name')?.value?.trim();
  const ram  = parseInt(document.getElementById('nf-ram')?.value, 10);
  const vcpu = parseInt(document.getElementById('nf-vcpu')?.value, 10);
  const disk = parseInt(document.getElementById('nf-disk')?.value, 10);
  const allowed_role = document.getElementById('nf-role')?.value;

  if (!name) { toast('Ingresa un nombre para el flavor', 'error'); return; }
  if (!ram || !vcpu || !disk) { toast('RAM, vCPU y disco deben ser mayores a 0', 'error'); return; }

  try {
    await api('POST', '/flavors/', { name, ram, vcpu, disk, allowed_role });
    toast(`Flavor "${name}" creado`, 'success');
    renderFlavors();
  } catch (e) { toast(e.message, 'error'); }
}
