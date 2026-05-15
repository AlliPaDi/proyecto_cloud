-- db/seeds/full_pipeline_seed.sql
-- Simula el estado completo del sistema con un slice de 3 VMs en topología lineal.
-- Prerequisito: init_schema.sql ya ejecutado (tablas + vlan_pool + workers + config).
--
-- Estado final simulado:
--   - 3 usuarios (SYSTEM_ADMIN, SLICE_ADMIN, STUDENT)
--   - Workers con recursos descubiertos (simula Monitoring)
--   - 1 Slice aprobado con Vlan-Slice 150
--   - 3 VMs colocadas en Workers (Round Robin: S1, S2, S3)
--   - 2 enlaces (VM1-VM2 remoto, VM2-VM3 remoto)
--   - Interfaces con IPs asignadas
--   - 3 tareas en PLACEMENT_READY listas para el Dispatcher

-- ============================================================
-- 1. USUARIOS (Auth)
-- ============================================================
-- Password: "admin123" hasheado con bcrypt 12 rondas (placeholder)
INSERT INTO users (username, password_hash, role) VALUES
  ('sysadmin', '$2b$12$LJ3m4ys3GZ7r9R8xQZ7K5OhJ5Z3K5OhJ5Z3K5OhJ5Z3K5OhJ5a', 'SYSTEM_ADMIN');

INSERT INTO users (username, password_hash, role) VALUES
  ('profesor1', '$2b$12$LJ3m4ys3GZ7r9R8xQZ7K5OhJ5Z3K5OhJ5Z3K5OhJ5Z3K5OhJ5a', 'SLICE_ADMIN');

INSERT INTO users (username, password_hash, role, admin_id) VALUES
  ('alumno1', '$2b$12$LJ3m4ys3GZ7r9R8xQZ7K5OhJ5Z3K5OhJ5Z3K5OhJ5Z3K5OhJ5a', 'STUDENT', 2);

-- ============================================================
-- 2. WORKERS CON RECURSOS (Monitoring)
-- ============================================================
UPDATE workers SET total_ram = 8192, total_cpu = 4,
  current_cpu_load = 15.30, current_ram_available = 7680,
  status = 'ALIVE' WHERE id = 1;

UPDATE workers SET total_ram = 8192, total_cpu = 4,
  current_cpu_load = 22.10, current_ram_available = 6144,
  status = 'ALIVE' WHERE id = 2;

UPDATE workers SET total_ram = 8192, total_cpu = 4,
  current_cpu_load = 8.50, current_ram_available = 7168,
  status = 'ALIVE' WHERE id = 3;

-- ============================================================
-- 3. SLICE APROBADO (Slice Manager + Networking)
-- ============================================================
-- Marcar VLAN 150 como usada
UPDATE vlan_pool SET status = 'USED' WHERE vlan_id = 150;

INSERT INTO slices (user_id, name, vlan_slice, status) VALUES
  (3, 'Topo-Lineal-3VMs', 150, 'ACTIVE');

-- ============================================================
-- 4. VMs COLOCADAS (VM Placement - Round Robin)
-- ============================================================
INSERT INTO virtual_machines (slice_id, name, base_image, ram, vcpu, worker_id, instance_path, status) VALUES
  (1, 'VM1', 'ubuntu-22.04.qcow2', 512, 1, 1, '/mnt/storage/instances/1.qcow2', 'PENDING_APPROVAL'),
  (1, 'VM2', 'ubuntu-22.04.qcow2', 512, 1, 2, '/mnt/storage/instances/2.qcow2', 'PENDING_APPROVAL'),
  (1, 'VM3', 'ubuntu-22.04.qcow2', 512, 1, 3, '/mnt/storage/instances/3.qcow2', 'PENDING_APPROVAL');

-- Actualizar puntero Round Robin
UPDATE config SET value = '3' WHERE key = 'last_worker_id';

-- ============================================================
-- 5. REDES / ENLACES (Networking)
-- ============================================================
-- Enlace 1: VM1(S1) <-> VM2(S2) → remoto, Vlan-Inner 100
INSERT INTO networks (slice_id, vlan_inner, subnet_cidr, is_remote) VALUES
  (1, 100, '192.168.1.0/24', TRUE);

-- Enlace 2: VM2(S2) <-> VM3(S3) → remoto, Vlan-Inner 200
INSERT INTO networks (slice_id, vlan_inner, subnet_cidr, is_remote) VALUES
  (1, 200, '192.168.2.0/24', TRUE);

-- ============================================================
-- 6. INTERFACES DE VM (Networking - IPAM)
-- ============================================================
-- VM1: 1 interfaz (eth0 → enlace 1)
INSERT INTO vm_interfaces (vm_id, network_id, mac_address, ip_address, interface_name, tap_name) VALUES
  (1, 1, '52:54:00:01:00:01', '192.168.1.1', 'eth0', 'tap-vm1-eth0');

-- VM2: 2 interfaces (eth0 → enlace 1, eth1 → enlace 2)
INSERT INTO vm_interfaces (vm_id, network_id, mac_address, ip_address, interface_name, tap_name) VALUES
  (2, 1, '52:54:00:02:00:01', '192.168.1.2', 'eth0', 'tap-vm2-eth0'),
  (2, 2, '52:54:00:02:01:01', '192.168.2.1', 'eth1', 'tap-vm2-eth1');

-- VM3: 1 interfaz (eth0 → enlace 2)
INSERT INTO vm_interfaces (vm_id, network_id, mac_address, ip_address, interface_name, tap_name) VALUES
  (3, 2, '52:54:00:03:00:01', '192.168.2.2', 'eth0', 'tap-vm3-eth0');

-- ============================================================
-- 7. TAREAS LISTAS PARA DESPACHO (Placement → Dispatcher)
-- ============================================================
INSERT INTO tasks (slice_id, vm_id, task_type, status, worker_id, payload) VALUES
  (1, 1, 'CREATE_VM', 'PLACEMENT_READY', 1, '{
    "vm_name": "VM1",
    "base_image": "ubuntu-22.04.qcow2",
    "base_path": "/mnt/storage/base/ubuntu-22.04.qcow2",
    "instance_path": "/mnt/storage/instances/1.qcow2",
    "ram": 512, "vcpu": 1,
    "slice_id": 1, "vlan_slice": 150,
    "bridge_name": "br-sl-1",
    "interfaces": [
      {"interface_name":"eth0","tap_name":"tap-vm1-eth0","vlan_inner":100,"ip_address":"192.168.1.1","mac_address":"52:54:00:01:00:01","network_id":1,"is_remote":true}
    ]
  }'),
  (1, 2, 'CREATE_VM', 'PLACEMENT_READY', 2, '{
    "vm_name": "VM2",
    "base_image": "ubuntu-22.04.qcow2",
    "base_path": "/mnt/storage/base/ubuntu-22.04.qcow2",
    "instance_path": "/mnt/storage/instances/2.qcow2",
    "ram": 512, "vcpu": 1,
    "slice_id": 1, "vlan_slice": 150,
    "bridge_name": "br-sl-1",
    "interfaces": [
      {"interface_name":"eth0","tap_name":"tap-vm2-eth0","vlan_inner":100,"ip_address":"192.168.1.2","mac_address":"52:54:00:02:00:01","network_id":1,"is_remote":true},
      {"interface_name":"eth1","tap_name":"tap-vm2-eth1","vlan_inner":200,"ip_address":"192.168.2.1","mac_address":"52:54:00:02:01:01","network_id":2,"is_remote":true}
    ]
  }'),
  (1, 3, 'CREATE_VM', 'PLACEMENT_READY', 3, '{
    "vm_name": "VM3",
    "base_image": "ubuntu-22.04.qcow2",
    "base_path": "/mnt/storage/base/ubuntu-22.04.qcow2",
    "instance_path": "/mnt/storage/instances/3.qcow2",
    "ram": 512, "vcpu": 1,
    "slice_id": 1, "vlan_slice": 150,
    "bridge_name": "br-sl-1",
    "interfaces": [
      {"interface_name":"eth0","tap_name":"tap-vm3-eth0","vlan_inner":200,"ip_address":"192.168.2.2","mac_address":"52:54:00:03:00:01","network_id":2,"is_remote":true}
    ]
  }');
