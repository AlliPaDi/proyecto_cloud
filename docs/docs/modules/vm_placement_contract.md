# VM Placement — Contrato de API (Puerto 8086)

## Endpoints

### GET /placement/status
Estado del scheduler.

**Output (200):**
```json
{
  "last_worker_id": 2,
  "tasks_pending": 3,
  "tasks_placement_ready": 1,
  "algorithm": "round_robin"
}
```

---

### POST /placement/trigger
Forzar una iteración del loop de placement (debug).

**Output (200):**
```json
{
  "tasks_processed": 3,
  "assignments": [
    {"task_id": 1, "vm_id": 1, "worker_id": 1, "status": "PLACEMENT_READY"},
    {"task_id": 2, "vm_id": 2, "worker_id": 2, "status": "PLACEMENT_READY"},
    {"task_id": 3, "vm_id": 3, "worker_id": 3, "status": "PLACEMENT_READY"}
  ],
  "skipped": []
}
```

**Posibles skips:**
```json
{
  "skipped": [
    {"task_id": 4, "reason": "No worker with sufficient RAM (needed: 2048, best_available: 1024)"},
    {"task_id": 5, "reason": "User quota exceeded (quota_cpu: 4, used: 4)"}
  ]
}
```

---

## Lógica interna (Loop)
```
1. SELECT tasks WHERE status = 'PENDING' ORDER BY created_at
2. Para cada tarea:
   a. Lee last_worker_id de tabla config
   b. Calcula next_worker = (last_worker_id % 3) + 1
   c. Si worker.status != 'ALIVE' → salta al siguiente
   d. Si worker.current_ram_available < vm.ram → salta
   e. Verifica cuota del usuario (quota_ram, quota_cpu)
   f. Si pasa → UPDATE task SET status='PLACEMENT_READY', worker_id={next}
   g. UPDATE config SET value={next} WHERE key='last_worker_id'
   h. UPDATE virtual_machines SET worker_id={next}
```

## Seed SQL para testing
```sql
-- Requiere: init_schema.sql + usuarios + slice aprobado
INSERT INTO users (username, password_hash, role) VALUES
  ('sysadmin', '$2b$12$placeholder', 'SYSTEM_ADMIN');
INSERT INTO users (username, password_hash, role) VALUES
  ('profesor1', '$2b$12$placeholder', 'SLICE_ADMIN');
INSERT INTO users (username, password_hash, role, admin_id) VALUES
  ('alumno1', '$2b$12$placeholder', 'STUDENT', 2);

-- Workers con recursos
UPDATE workers SET total_ram=8192, total_cpu=4, current_ram_available=8192, status='ALIVE';

-- Slice ya aprobado
INSERT INTO slices (user_id, name, vlan_slice, status) VALUES
  (3, 'Topo-Test', 150, 'ACTIVE');

-- VMs sin worker asignado aún
INSERT INTO virtual_machines (slice_id, name, base_image, ram, vcpu, status) VALUES
  (1, 'VM1', 'ubuntu-22.04.qcow2', 512, 1, 'PENDING_APPROVAL'),
  (1, 'VM2', 'ubuntu-22.04.qcow2', 512, 1, 'PENDING_APPROVAL'),
  (1, 'VM3', 'ubuntu-22.04.qcow2', 512, 1, 'PENDING_APPROVAL');

-- Tareas PENDING para que el Placement las procese
INSERT INTO tasks (slice_id, vm_id, task_type, status, payload) VALUES
  (1, 1, 'CREATE_VM', 'PENDING', '{"vm_name":"VM1","base_image":"ubuntu-22.04.qcow2","ram":512,"vcpu":1}'),
  (1, 2, 'CREATE_VM', 'PENDING', '{"vm_name":"VM2","base_image":"ubuntu-22.04.qcow2","ram":512,"vcpu":1}'),
  (1, 3, 'CREATE_VM', 'PENDING', '{"vm_name":"VM3","base_image":"ubuntu-22.04.qcow2","ram":512,"vcpu":1}');
```

## Test cURL
```bash
# Ver estado del scheduler
curl http://localhost:8086/placement/status

# Forzar iteración de placement
curl -X POST http://localhost:8086/placement/trigger

# Verificar que las tareas cambiaron a PLACEMENT_READY
# (consultar directamente la BD)
```
