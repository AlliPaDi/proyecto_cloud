# Networking — Contrato de API (Puerto 8085)

## Endpoints

### POST /networking/allocate
Recibe topología + mapa de placement. Asigna Vlan-Slice, Vlan-Inners, clasifica enlaces y asigna IPs.

**Input:**
```json
{
  "slice_id": 1,
  "placement_map": {
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 1,
    "5": 2,
    "6": 3
  },
  "links": [
    {"link_name": "link-A", "vm_a_id": 1, "iface_a": "eth1", "vm_b_id": 4, "iface_b": "eth0"},
    {"link_name": "link-B", "vm_a_id": 1, "iface_a": "eth0", "vm_b_id": 2, "iface_b": "eth0"},
    {"link_name": "link-C", "vm_a_id": 2, "iface_a": "eth1", "vm_b_id": 3, "iface_b": "eth1"},
    {"link_name": "link-D", "vm_a_id": 3, "iface_a": "eth0", "vm_b_id": 4, "iface_b": "eth1"},
    {"link_name": "link-E", "vm_a_id": 4, "iface_a": "eth2", "vm_b_id": 5, "iface_b": "eth0"},
    {"link_name": "link-F", "vm_a_id": 5, "iface_a": "eth1", "vm_b_id": 6, "iface_b": "eth0"}
  ]
}
```

- `placement_map`: `{vm_id: worker_id}` — necesario para clasificar enlaces como local/remoto.
- `links`: cada enlace define las dos interfaces que se conectan.

**Output (200):**
```json
{
  "slice_id": 1,
  "vlan_slice": 150,
  "bridge_name": "br-sl-1",
  "networks": [
    {
      "network_id": 1,
      "link_name": "link-A",
      "vlan_inner": 0,
      "subnet_cidr": "192.168.1.0/24",
      "is_remote": false,
      "interfaces": [
        {"vm_id": 1, "interface_name": "eth1", "tap_name": "tap-vm1-eth1", "ip_address": "192.168.1.1", "mac_address": "52:54:00:01:01:01"},
        {"vm_id": 4, "interface_name": "eth0", "tap_name": "tap-vm4-eth0", "ip_address": "192.168.1.2", "mac_address": "52:54:00:04:00:01"}
      ]
    },
    {
      "network_id": 2,
      "link_name": "link-B",
      "vlan_inner": 200,
      "subnet_cidr": "192.168.2.0/24",
      "is_remote": true,
      "interfaces": [
        {"vm_id": 1, "interface_name": "eth0", "tap_name": "tap-vm1-eth0", "ip_address": "192.168.2.1", "mac_address": "52:54:00:01:00:01"},
        {"vm_id": 2, "interface_name": "eth0", "tap_name": "tap-vm2-eth0", "ip_address": "192.168.2.2", "mac_address": "52:54:00:02:00:01"}
      ]
    }
  ]
}
```

**Errores:**
- `409`: No hay VLANs disponibles en el pool.
- `400`: `slice_id` no existe o `placement_map` incompleto.

---

### POST /networking/release
Libera la Vlan-Slice y limpia los registros de red.

**Input:**
```json
{
  "slice_id": 1
}
```

**Output (200):**
```json
{
  "released_vlan_slice": 150,
  "networks_deleted": 6,
  "interfaces_deleted": 12
}
```

---

### GET /networking/vlans/available
**Output (200):**
```json
{
  "total": 901,
  "available": 897,
  "used": 4
}
```

---

## Seed SQL para testing
```sql
-- Requiere: init_schema.sql ya ejecutado (vlan_pool, workers ya existen)
-- Crear usuarios y slice de prueba

INSERT INTO users (username, password_hash, role) VALUES
  ('sysadmin', '$2b$12$placeholder', 'SYSTEM_ADMIN');
INSERT INTO users (username, password_hash, role, admin_id) VALUES
  ('alumno1', '$2b$12$placeholder', 'STUDENT', 1);

-- Slice sin vlan_slice aún (el Networking lo asigna)
INSERT INTO slices (user_id, name, status) VALUES
  (2, 'Topo-Lineal-6VMs', 'PENDING_APPROVAL');

-- VMs ya con placement asignado
INSERT INTO virtual_machines (slice_id, name, base_image, ram, vcpu, worker_id, status) VALUES
  (1, 'VM1', 'ubuntu-22.04.qcow2', 512, 1, 1, 'PENDING_APPROVAL'),
  (1, 'VM2', 'ubuntu-22.04.qcow2', 512, 1, 2, 'PENDING_APPROVAL'),
  (1, 'VM3', 'ubuntu-22.04.qcow2', 512, 1, 3, 'PENDING_APPROVAL'),
  (1, 'VM4', 'ubuntu-22.04.qcow2', 512, 1, 1, 'PENDING_APPROVAL'),
  (1, 'VM5', 'ubuntu-22.04.qcow2', 512, 1, 2, 'PENDING_APPROVAL'),
  (1, 'VM6', 'ubuntu-22.04.qcow2', 512, 1, 3, 'PENDING_APPROVAL');
```

## Test cURL
```bash
# Asignar red a la topología
curl -X POST http://localhost:8085/networking/allocate \
  -H "Content-Type: application/json" \
  -d '{
    "slice_id": 1,
    "placement_map": {"1":1,"2":2,"3":3,"4":1,"5":2,"6":3},
    "links": [
      {"link_name":"link-A","vm_a_id":1,"iface_a":"eth1","vm_b_id":4,"iface_b":"eth0"},
      {"link_name":"link-B","vm_a_id":1,"iface_a":"eth0","vm_b_id":2,"iface_b":"eth0"},
      {"link_name":"link-C","vm_a_id":2,"iface_a":"eth1","vm_b_id":3,"iface_b":"eth1"},
      {"link_name":"link-D","vm_a_id":3,"iface_a":"eth0","vm_b_id":4,"iface_b":"eth1"},
      {"link_name":"link-E","vm_a_id":4,"iface_a":"eth2","vm_b_id":5,"iface_b":"eth0"},
      {"link_name":"link-F","vm_a_id":5,"iface_a":"eth1","vm_b_id":6,"iface_b":"eth0"}
    ]
  }'

# VLANs disponibles
curl http://localhost:8085/networking/vlans/available

# Liberar red
curl -X POST http://localhost:8085/networking/release \
  -H "Content-Type: application/json" \
  -d '{"slice_id": 1}'
```
