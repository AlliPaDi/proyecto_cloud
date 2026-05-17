# Slice Manager — Contrato de API (Puerto 8082)

## Endpoints

### POST /slices/
Crea una solicitud de Slice (rol: STUDENT).

**Headers:** `X-User-Role: STUDENT`, `X-User-Id: 2`

**Input:**
```json
{
  "name": "Topo-Lineal-3VMs",
  "vms": [
    {"name": "VM1", "base_image": "ubuntu-22.04.qcow2", "ram": 512, "vcpu": 1},
    {"name": "VM2", "base_image": "ubuntu-22.04.qcow2", "ram": 512, "vcpu": 1},
    {"name": "VM3", "base_image": "ubuntu-22.04.qcow2", "ram": 512, "vcpu": 1}
  ],
  "links": [
    {"vm_a": "VM1", "iface_a": "eth0", "vm_b": "VM2", "iface_b": "eth0"},
    {"vm_a": "VM2", "iface_a": "eth1", "vm_b": "VM3", "iface_b": "eth0"}
  ]
}
```

**Output (201):**
```json
{
  "slice_id": 1,
  "name": "Topo-Lineal-3VMs",
  "status": "PENDING_APPROVAL",
  "vms": [
    {"id": 1, "name": "VM1", "status": "PENDING_APPROVAL"},
    {"id": 2, "name": "VM2", "status": "PENDING_APPROVAL"},
    {"id": 3, "name": "VM3", "status": "PENDING_APPROVAL"}
  ],
  "links_count": 2
}
```

**Errores:**
- `400`: Imagen base no existe (validado con Image Manager).
- `403`: Cuota excedida (suma de RAM/vCPU supera `quota_ram`/`quota_cpu` del usuario).

---

### GET /slices/
Listar slices del usuario autenticado.

**Headers:** `X-User-Role: STUDENT`, `X-User-Id: 2`

**Output (200):**
```json
{
  "slices": [
    {"id": 1, "name": "Topo-Lineal-3VMs", "status": "PENDING_APPROVAL", "vms_count": 3, "created_at": "2026-05-12T10:00:00"}
  ]
}
```

---

### GET /slices/{id}
Detalle con VMs, IPs, PIDs, VNC ports.

**Output (200):**
```json
{
  "id": 1,
  "name": "Topo-Lineal-3VMs",
  "status": "ACTIVE",
  "vlan_slice": 150,
  "vms": [
    {
      "id": 1, "name": "VM1", "worker_id": 1, "status": "READY",
      "process_id": 12345, "vnc_port": 5901,
      "interfaces": [
        {"interface_name": "eth0", "ip_address": "192.168.1.1", "tap_name": "tap-vm1-eth0", "vlan_inner": 100}
      ]
    }
  ]
}
```

---

### POST /slices/{id}/approve
Aprueba un Slice (rol: SLICE_ADMIN).

**Headers:** `X-User-Role: SLICE_ADMIN`, `X-User-Id: 1`

**Output (200):**
```json
{
  "slice_id": 1,
  "status": "ACTIVE",
  "tasks_created": 3,
  "message": "Slice aprobado. 3 tareas de tipo CREATE_VM generadas."
}
```

**Errores:**
- `403`: Rol no autorizado o el alumno no pertenece a este SLICE_ADMIN.
- `409`: Slice ya fue aprobado/rechazado.

---

### POST /slices/{id}/reject
Rechaza un Slice.

**Output (200):**
```json
{
  "slice_id": 1,
  "status": "REJECTED",
  "message": "Slice rechazado."
}
```

---

### DELETE /slices/{id}
Borrado inteligente.

**Output (200):**
```json
{
  "slice_id": 1,
  "status": "DELETED",
  "cleanup": {
    "vms_terminated": 3,
    "networks_released": 2,
    "vlan_slice_freed": 150
  }
}
```

---

## Flujo interno del Slice Manager
```
POST /slices/ (Student)
  → Valida imagen con Image Manager (GET /images/{name}/validate)
  → Inserta en BD: slices + virtual_machines (PENDING_APPROVAL)
  → Retorna confirmación

POST /slices/{id}/approve (Slice Admin)
  → VM Placement asigna Workers (Round Robin)
  → Networking asigna Vlan-Slice, Vlan-Inners, IPs (POST /networking/allocate)
  → Inserta tasks (una por VM, tipo CREATE_VM, status PENDING)
```

## Seed SQL para testing
```sql
INSERT INTO users (username, password_hash, role) VALUES
  ('sysadmin', '$2b$12$placeholder', 'SYSTEM_ADMIN');
INSERT INTO users (username, password_hash, role) VALUES
  ('profesor1', '$2b$12$placeholder', 'SLICE_ADMIN');
INSERT INTO users (username, password_hash, role, admin_id) VALUES
  ('alumno1', '$2b$12$placeholder', 'STUDENT', 2);

-- Workers con recursos (simula que Monitoring ya descubrió)
UPDATE workers SET total_ram=8192, total_cpu=4, current_ram_available=8192, status='ALIVE';
```

## Test cURL
```bash
# Crear slice (como STUDENT)
curl -X POST http://localhost:8082/slices/ \
  -H "Content-Type: application/json" \
  -H "X-User-Role: STUDENT" -H "X-User-Id: 3" \
  -d '{
    "name": "Topo-Lineal-3VMs",
    "vms": [
      {"name":"VM1","base_image":"ubuntu-22.04.qcow2","ram":512,"vcpu":1},
      {"name":"VM2","base_image":"ubuntu-22.04.qcow2","ram":512,"vcpu":1},
      {"name":"VM3","base_image":"ubuntu-22.04.qcow2","ram":512,"vcpu":1}
    ],
    "links": [
      {"vm_a":"VM1","iface_a":"eth0","vm_b":"VM2","iface_b":"eth0"},
      {"vm_a":"VM2","iface_a":"eth1","vm_b":"VM3","iface_b":"eth0"}
    ]
  }'

# Aprobar slice (como SLICE_ADMIN)
curl -X POST http://localhost:8082/slices/1/approve \
  -H "X-User-Role: SLICE_ADMIN" -H "X-User-Id: 2"

# Ver detalle
curl http://localhost:8082/slices/1 \
  -H "X-User-Role: STUDENT" -H "X-User-Id: 3"
```
