// ── Monitoreo de Recursos (SYSTEM_ADMIN): inventario + telemetría ─
// GET /infra/metrics → Monitoring: por cluster (linux/openstack), lista de
// nodos con hardware_total, resources_assigned (VMs colocadas) y
// resources_utilized (telemetría real vía SSH), refrescado cada 4s.

const MONITOR_CLUSTER_LABELS = { linux: 'Linux Cluster', openstack: 'OpenStack Cluster' };
const MONITOR_CLUSTER_ORDER = ['linux', 'openstack'];

let monitorInterval = null;
let monitorTab = 'linux';

function stopMonitoring() {
  if (monitorInterval) {
    clearInterval(monitorInterval);
    monitorInterval = null;
  }
}

async function renderMonitoring() {
  const seq = beginRender();
  const content = document.getElementById('content');
  content.innerHTML = `<div class="text-muted">Cargando...</div>`;

  const tick = async () => {
    try {
      const data = await api('GET', '/infra/metrics');
      if (isStale(seq)) { stopMonitoring(); return; }
      renderMonitoringContent(data.clusters || []);
    } catch (e) {
      if (isStale(seq)) return;
      stopMonitoring();
      content.innerHTML = `<div class="card"><p class="error-msg">${esc(e.message)}</p></div>`;
    }
  };

  await tick();
  if (!isStale(seq)) {
    monitorInterval = setInterval(tick, 4000);
  }
}

function renderMonitoringContent(clusters) {
  const content = document.getElementById('content');

  const byType = {};
  clusters.forEach(c => { byType[c.cluster_type] = c.nodes || []; });
  if (!MONITOR_CLUSTER_ORDER.includes(monitorTab)) monitorTab = 'linux';

  const tabsHTML = MONITOR_CLUSTER_ORDER.map(t => `
    <button class="mon-tab ${monitorTab === t ? 'active' : ''}" data-tab="${t}">
      ${MONITOR_CLUSTER_LABELS[t]}
    </button>
  `).join('');

  const nodes = byType[monitorTab] || [];

  content.innerHTML = `
    <div class="mon-tabs">${tabsHTML}</div>
    ${nodes.length === 0
      ? '<div class="card"><div class="empty-state"><div class="empty-icon">🖥️</div><p>No hay servidores registrados para este clúster.</p></div></div>'
      : `<div class="mon-grid">${nodes.map(monitorNodeCard).join('')}</div>`}
  `;

  content.querySelectorAll('.mon-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      monitorTab = btn.dataset.tab;
      renderMonitoringContent(clusters);
    });
  });
}

function monitorNodeCard(n) {
  const hw = n.hardware_total, asg = n.resources_assigned, use = n.resources_utilized;
  return `
    <div class="mon-node-card">
      <div class="mon-node-header">
        <strong>${esc(n.node_name)}</strong>
        ${badge(n.status || 'ALIVE')}
      </div>
      <div class="text-muted text-sm mon-node-hw">${hw.cores} cores · ${hw.ram_gb.toFixed(1)} GB RAM (hardware total)</div>
      ${monitorMetricBar('CPU', asg.cores, use.cores, hw.cores, 'cores')}
      ${monitorMetricBar('RAM', asg.ram_gb, use.ram_gb, hw.ram_gb, 'GB')}
    </div>`;
}

function monitorMetricBar(label, assigned, used, total, unit) {
  const safeTotal = total > 0 ? total : 1;
  const assignedPct = Math.min(100, (assigned / safeTotal) * 100);
  const usedPct = Math.min(100, (used / safeTotal) * 100);
  const pctOfAssigned = assigned > 0 ? (used / assigned) * 100 : 0;

  let colorClass = 'ok';
  if (pctOfAssigned >= 95) colorClass = 'danger';
  else if (pctOfAssigned >= 80) colorClass = 'warn';

  return `
    <div class="mon-metric">
      <div class="mon-metric-label">
        <span>${label}</span>
        <span class="text-muted text-sm">${used.toFixed(2)} / ${assigned.toFixed(2)} ${unit} asignados</span>
      </div>
      <div class="mon-bar-track" title="Hardware total: ${total.toFixed(2)} ${unit}">
        <div class="mon-bar-assigned" style="width:${assignedPct}%"></div>
        <div class="mon-bar-used ${colorClass}" style="width:${usedPct}%"></div>
      </div>
      <div class="mon-bar-legend text-xs text-muted">
        <span>Total: ${total.toFixed(2)} ${unit}</span>
        <span>${pctOfAssigned.toFixed(0)}% del límite asignado</span>
      </div>
    </div>`;
}
