# Dispatcher + Driver — Contrato de API (Puertos 8087 / 8088)

## DISPATCHER (Puerto 8087)

### GET /dispatcher/status
**Output (200):**
```json
{
  "polling_active": true,
  "tasks_in_progress": 2,
  "tasks_completed_last_hour": 5,
  "tasks_failed_last_hour": 0
}
```

---

### POST /dispatcher/trigger
Forzar una iteración del loop de despacho.

**Output (200):**
```json
{
  "dispatched": [
    {"task_id": 1, "vm_id": 1, "worker_ip": "10.0.10.1", "status": "IN_PROGRESS"}
  ]
}
```

---

## DRIVER (Puerto 8088)

### POST /driver/execute
Ejecuta una tarea de despliegue en un Worker.

**Input (enviado por el Dispatcher):**
```json
{
  "task_id": 1,
  "task_type": "CREATE_VM",
  "worker_ip": "10.0.10.1",
  "vm": {
    "id": 1,
    "name": "VM1",
    "base_image": "ubuntu-22.04.qcow2",
    "ram": 512,
    "vcpu": 1,
    "instance_path": "/mnt/storage/instances/1.qcow2"
  },
  "slice": {
    "id": 1,
    "vlan_slice": 150
  },
  "interfaces": [
    {
      "interface_name": "eth0",
      "tap_name": "tap-vm1-eth0",
      "vlan_inner": 200,
      "ip_address": "192.168.2.1",
      "mac_address": "52:54:00:01:00:01",
      "bridge_name": "br-sl-1",
      "is_remote": true
    },
    {
      "interface_name": "eth1",
      "tap_name": "tap-vm1-eth1",
      "vlan_inner": 0,
      "ip_address": "192.168.1.1",
      "mac_address": "52:54:00:01:01:01",
      "bridge_name": "br-sl-1",
      "is_remote": false
    }
  ]
}
```

**Output (200) — Éxito:**
```json
{
  "task_id": 1,
  "status": "READY",
  "process_id": 12345,
  "vnc_port": 5901,
  "commands_executed": [
    "qemu-img create -f qcow2 -b /mnt/storage/base/ubuntu-22.04.qcow2 /mnt/storage/instances/1.qcow2",
    "ovs-vsctl --may-exist add-br br-wk",
    "ovs-vsctl --may-exist add-br br-sl-1",
    "ovs-vsctl add-port br-sl-1 tap-vm1-eth0 tag=200",
    "ovs-vsctl add-port br-sl-1 tap-vm1-eth1 tag=0",
    "ovs-vsctl add-port br-sl-1 patch-to-wk-1 -- set interface patch-to-wk-1 type=patch options:peer=patch-to-sl-1",
    "ovs-vsctl add-port br-wk patch-to-sl-1 tag=150 -- set interface patch-to-sl-1 type=patch options:peer=patch-to-wk-1"
  ]
}
```

**Output (500) — Fallo con rollback:**
```json
{
  "task_id": 1,
  "status": "FAILED",
  "error_msg": "SSH connection refused to 10.0.10.1",
  "rollback_actions": [
    "Deleted TAP tap-vm1-eth0 from br-sl-1",
    "Deleted disk /mnt/storage/instances/1.qcow2"
  ]
}
```

---

## Secuencia de comandos SSH del Driver
```bash
# 1. Crear disco (Thin Provisioning)
qemu-img create -f qcow2 -b /mnt/storage/base/ubuntu-22.04.qcow2 /mnt/storage/instances/1.qcow2

# 2. Bridges (idempotentes)
ovs-vsctl --may-exist add-br br-wk
ovs-vsctl --may-exist add-port br-wk ens4
ovs-vsctl --may-exist add-br br-sl-1

# 3. TAPs con Vlan-Inner
ovs-vsctl add-port br-sl-1 tap-vm1-eth0 tag=200
ovs-vsctl add-port br-sl-1 tap-vm1-eth1 tag=0

# 4. Patch Ports (solo enlaces remotos, tag=Vlan-Slice)
ovs-vsctl add-port br-sl-1 patch-to-wk-1 \
  -- set interface patch-to-wk-1 type=patch options:peer=patch-to-sl-1
ovs-vsctl add-port br-wk patch-to-sl-1 tag=150 \
  -- set interface patch-to-sl-1 type=patch options:peer=patch-to-wk-1

# 5. Lanzar QEMU
qemu-system-x86_64 \
  -m 512 -smp 1 \
  -drive file=/mnt/storage/instances/1.qcow2,format=qcow2 \
  -netdev tap,id=net0,ifname=tap-vm1-eth0,script=no,downscript=no \
  -device virtio-net-pci,netdev=net0,mac=52:54:00:01:00:01 \
  -netdev tap,id=net1,ifname=tap-vm1-eth1,script=no,downscript=no \
  -device virtio-net-pci,netdev=net1,mac=52:54:00:01:01:01 \
  -pidfile /tmp/VM1.pid \
  -vnc :1 -daemonize

# 6. Leer PID
cat /tmp/VM1.pid
```

## Seed SQL para testing
```sql
-- Requiere: todo el pipeline previo (usuarios, workers, slice, VMs, networks)
INSERT INTO users (username, password_hash, role) VALUES
  ('sysadmin', '$2b$12$placeholder', 'SYSTEM_ADMIN');
INSERT INTO users (username, password_hash, role, admin_id) VALUES
  ('alumno1', '$2b$12$placeholder', 'STUDENT', 1);

UPDATE workers SET total_ram=8192, total_cpu=4, current_ram_available=8192, status='ALIVE';

INSERT INTO slices (user_id, name, vlan_slice, status) VALUES
  (2, 'Topo-Test', 150, 'ACTIVE');

INSERT INTO virtual_machines (slice_id, name, base_image, ram, vcpu, worker_id, instance_path, status) VALUES
  (1, 'VM1', 'ubuntu-22.04.qcow2', 512, 1, 1, '/mnt/storage/instances/1.qcow2', 'PENDING_APPROVAL');

INSERT INTO networks (slice_id, vlan_inner, subnet_cidr, is_remote) VALUES
  (1, 200, '192.168.2.0/24', TRUE),
  (1, 0, '192.168.1.0/24', FALSE);

INSERT INTO vm_interfaces (vm_id, network_id, mac_address, ip_address, interface_name, tap_name) VALUES
  (1, 1, '52:54:00:01:00:01', '192.168.2.1', 'eth0', 'tap-vm1-eth0'),
  (1, 2, '52:54:00:01:01:01', '192.168.1.1', 'eth1', 'tap-vm1-eth1');

-- Tarea lista para el Dispatcher
INSERT INTO tasks (slice_id, vm_id, task_type, status, worker_id, payload) VALUES
  (1, 1, 'CREATE_VM', 'PLACEMENT_READY', 1, '{
    "vm_name":"VM1","base_image":"ubuntu-22.04.qcow2","ram":512,"vcpu":1,
    "instance_path":"/mnt/storage/instances/1.qcow2"
  }');
```

## Test cURL
```bash
# Verificar estado del Dispatcher
curl http://localhost:8087/dispatcher/status

# Forzar despacho
curl -X POST http://localhost:8087/dispatcher/trigger

# Ejecutar directamente en el Driver (bypassing Dispatcher, para debug)
curl -X POST http://localhost:8088/driver/execute \
  -H "Content-Type: application/json" \
  -d '{ "task_id":1, "task_type":"CREATE_VM", "worker_ip":"10.0.10.1",
    "vm":{"id":1,"name":"VM1","base_image":"ubuntu-22.04.qcow2","ram":512,"vcpu":1,"instance_path":"/mnt/storage/instances/1.qcow2"},
    "slice":{"id":1,"vlan_slice":150},
    "interfaces":[
      {"interface_name":"eth0","tap_name":"tap-vm1-eth0","vlan_inner":200,"ip_address":"192.168.2.1","mac_address":"52:54:00:01:00:01","bridge_name":"br-sl-1","is_remote":true}
    ]}'
```

## Configuración local
```bash
# Desactivar SSH para pruebas sin Workers reales
SSH_ENABLED=false
```
