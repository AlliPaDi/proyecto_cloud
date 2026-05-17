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
      "internet_access": false,
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
      "internet_access": false,
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

### GET /networking/networks/{slice_id}
Consulta el plan de red completo de un slice con todas sus redes e interfaces.

**Output (200):**
```json
{
  "slice_id": 1,
  "vlan_slice": 150,
  "bridge_name": "br-sl-1",
  "networks": [
    {
      "id": 1,
      "vlan_inner": 200,
      "subnet_cidr": "192.168.2.0/24",
      "is_remote": true,
      "internet_access": false,
      "interfaces": [
        {"vm_id": 1, "worker_id": 1, "mac_address": "52:54:00:01:00:01", "ip_address": "192.168.2.1", "interface_name": "eth0", "tap_name": "tap-vm1-eth0"},
        {"vm_id": 2, "worker_id": 2, "mac_address": "52:54:00:02:00:01", "ip_address": "192.168.2.2", "interface_name": "eth0", "tap_name": "tap-vm2-eth0"}
      ]
    }
  ]
}
```

---

## Generación de Comandos OVS

### GET /networking/ovs/commands/{slice_id}
Pre-calcula la lista exacta de comandos `ovs-vsctl` que el Driver debe ejecutar en cada Worker para desplegar la topología del slice.

**Output (200):**
```json
{
  "slice_id": 1,
  "vlan_slice": 150,
  "bridge_name": "br-sl-1",
  "workers": [
    {
      "worker_id": 1,
      "commands": [
        "ovs-vsctl --may-exist add-br br-sl-1",
        "ovs-vsctl add-port br-sl-1 tap-vm1-eth0 tag=200",
        "ovs-vsctl add-port br-sl-1 tap-vm1-eth1",
        "ovs-vsctl add-port br-sl-1 patch-to-wk-1 -- set interface patch-to-wk-1 type=patch options:peer=patch-to-sl-1",
        "ovs-vsctl add-port br-wk patch-to-sl-1 tag=150 -- set interface patch-to-sl-1 type=patch options:peer=patch-to-wk-1",
        "ovs-vsctl --may-exist add-port br-wk ens4"
      ]
    },
    {
      "worker_id": 2,
      "commands": [
        "ovs-vsctl --may-exist add-br br-sl-1",
        "ovs-vsctl add-port br-sl-1 tap-vm2-eth0 tag=200",
        "ovs-vsctl add-port br-sl-1 patch-to-wk-1 -- set interface patch-to-wk-1 type=patch options:peer=patch-to-sl-1",
        "ovs-vsctl add-port br-wk patch-to-sl-1 tag=150 -- set interface patch-to-sl-1 type=patch options:peer=patch-to-wk-1",
        "ovs-vsctl --may-exist add-port br-wk ens4"
      ]
    }
  ]
}
```

**Lógica interna:**
1. Crear `br-sl-{slice_id}` en cada Worker que tenga VMs del slice (idempotente).
2. Conectar cada TAP al Br-Slice con `tag={vlan_inner}` (sin tag si `vlan_inner=0`).
3. Para Workers con enlaces remotos: crear patch-ports Br-Slice ↔ Br-WK con `tag={vlan_slice}`.
4. Asegurar que `ens4` esté en `br-wk` como trunk (idempotente).

---

## Micro-Segmentación por OpenFlow (Security Rules)

### POST /networking/security/rules
Crea una regla de seguridad entre dos VMs del mismo slice.

**Input:**
```json
{
  "slice_id": 1,
  "src_vm_id": 1,
  "dst_vm_id": 2,
  "protocol": "tcp",
  "port_min": 80,
  "port_max": 80,
  "action": "ALLOW",
  "priority": 100
}
```

**Output (201):**
```json
{
  "id": 1,
  "slice_id": 1,
  "src_vm_id": 1,
  "dst_vm_id": 2,
  "protocol": "tcp",
  "port_min": 80,
  "port_max": 80,
  "action": "ALLOW",
  "priority": 100
}
```

**Validaciones:**
- `src_vm_id != dst_vm_id`
- `protocol` ∈ `{tcp, udp, icmp, any}`
- `action` ∈ `{ALLOW, DENY}`
- ICMP no admite puertos (`port_min`, `port_max` deben ser `null`).

---

### GET /networking/security/rules/{slice_id}
Lista todas las reglas de seguridad del slice.

**Output (200):** Array de `SecurityRuleResponse`.

---

### DELETE /networking/security/rules/{rule_id}
Elimina una regla de seguridad.

**Output (204):** Sin contenido.

---

### GET /networking/security/flows/{slice_id}
Genera las reglas OpenFlow (`ovs-ofctl`) listas para aplicar en el Br-Slice del slice.

**Output (200):**
```json
{
  "slice_id": 1,
  "setup_flows": [
    {"bridge": "br-sl-1", "flow": "priority=10,arp,actions=normal"},
    {"bridge": "br-sl-1", "flow": "priority=1,ip,actions=drop"}
  ],
  "policy_flows": [
    {"bridge": "br-sl-1", "flow": "priority=100,tcp,in_port=tap-vm1-eth0,nw_src=192.168.2.1,nw_dst=192.168.2.2,tp_dst=80,actions=normal"}
  ]
}
```

**Lógica:**
- `setup_flows`: Reglas base que se aplican siempre (ARP allow + default-deny IP).
- `policy_flows`: Reglas derivadas de `security_rules`. Solo se generan flows entre VMs que comparten la misma red (`network_id`).
- El Driver aplica estos flows con: `ovs-ofctl add-flow {bridge} {flow}`.

---

## NAT / Salida a Internet

### GET /networking/nat/commands/{slice_id}
Genera comandos `iptables` para redes del slice que tienen `internet_access=TRUE`.

**Output (200):**
```json
{
  "slice_id": 1,
  "nat_networks": [
    {
      "network_id": 5,
      "subnet_cidr": "10.150.5.0/24",
      "commands": [
        "sysctl -w net.ipv4.ip_forward=1",
        "iptables -t nat -A POSTROUTING -s 10.150.5.0/24 -o ens4 -j MASQUERADE",
        "iptables -A FORWARD -i ens4 -o br-sl-1 -m state --state RELATED,ESTABLISHED -j ACCEPT",
        "iptables -A FORWARD -i br-sl-1 -o ens4 -j ACCEPT"
      ]
    }
  ]
}
```

**Nota:** Si ninguna red del slice tiene `internet_access=TRUE`, retorna `nat_networks: []`.

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

# Consultar plan de red
curl http://localhost:8085/networking/networks/1

# Comandos OVS pre-calculados
curl http://localhost:8085/networking/ovs/commands/1

# Crear regla de seguridad
curl -X POST http://localhost:8085/networking/security/rules \
  -H "Content-Type: application/json" \
  -d '{"slice_id":1,"src_vm_id":1,"dst_vm_id":2,"protocol":"tcp","port_min":80,"port_max":80,"action":"ALLOW","priority":100}'

# Listar reglas de seguridad
curl http://localhost:8085/networking/security/rules/1

# Generar OpenFlow rules
curl http://localhost:8085/networking/security/flows/1

# Comandos NAT
curl http://localhost:8085/networking/nat/commands/1

# Liberar red
curl -X POST http://localhost:8085/networking/release \
  -H "Content-Type: application/json" \
  -d '{"slice_id": 1}'
```
