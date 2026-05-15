-- 1. LIMPIEZA PREVIA (Opcional, para evitar duplicados en esta sesión)
DELETE FROM tasks;
DELETE FROM vm_interfaces;
DELETE FROM virtual_machines;
DELETE FROM networks;
DELETE FROM slices;

-- 2. USUARIOS (Usamos ON CONFLICT para que no falle si ya existen)
INSERT INTO users (username, password_hash, role) VALUES
  ('sysadmin', 'hash', 'SYSTEM_ADMIN'),
  ('profesor1', 'hash', 'SLICE_ADMIN')
ON CONFLICT (username) DO NOTHING;

INSERT INTO users (username, password_hash, role, admin_id) VALUES
  ('alumno1', 'hash', 'STUDENT', (SELECT id FROM users WHERE username='profesor1'))
ON CONFLICT (username) DO NOTHING;

-- 3. SLICE (Y guardamos su ID)
INSERT INTO slices (user_id, name, status) 
VALUES ((SELECT id FROM users WHERE username='alumno1'), 'Topo-Lineal-3VMs', 'ACTIVE');

-- 4. REDES (Usando subconsultas para el slice_id recién creado)
UPDATE vlan_pool SET status = 'USED' WHERE vlan_id IN (100, 200);

INSERT INTO networks (slice_id, vlan_id, subnet_cidr, bridge_name) 
SELECT id, 100, '192.168.1.0/24', 'br-lk-100' FROM slices WHERE name='Topo-Lineal-3VMs';

INSERT INTO networks (slice_id, vlan_id, subnet_cidr, bridge_name) 
SELECT id, 200, '192.168.2.0/24', 'br-lk-200' FROM slices WHERE name='Topo-Lineal-3VMs';

-- 5. VMs
INSERT INTO virtual_machines (slice_id, name, base_image, ram, vcpu, worker_id, status)
SELECT id, 'VM1', 'ubuntu-22.04.qcow2', 512, 1, 1, 'PENDING_APPROVAL' FROM slices WHERE name='Topo-Lineal-3VMs';

INSERT INTO virtual_machines (slice_id, name, base_image, ram, vcpu, worker_id, status)
SELECT id, 'VM2', 'ubuntu-22.04.qcow2', 512, 1, 2, 'PENDING_APPROVAL' FROM slices WHERE name='Topo-Lineal-3VMs';

INSERT INTO virtual_machines (slice_id, name, base_image, ram, vcpu, worker_id, status)
SELECT id, 'VM3', 'ubuntu-22.04.qcow2', 512, 1, 3, 'PENDING_APPROVAL' FROM slices WHERE name='Topo-Lineal-3VMs';

-- 6. INTERFACES (Aquí es donde fallaba: buscamos el ID real de la VM y de la Red)
INSERT INTO vm_interfaces (vm_id, network_id, mac_address, ip_address, interface_name)
VALUES 
  ((SELECT id FROM virtual_machines WHERE name='VM1' LIMIT 1), (SELECT id FROM networks WHERE vlan_id=100 LIMIT 1), '52:54:00:01:00:01', '192.168.1.1', 'eth0'),
  ((SELECT id FROM virtual_machines WHERE name='VM2' LIMIT 1), (SELECT id FROM networks WHERE vlan_id=100 LIMIT 1), '52:54:00:02:00:01', '192.168.1.2', 'eth0'),
  ((SELECT id FROM virtual_machines WHERE name='VM2' LIMIT 1), (SELECT id FROM networks WHERE vlan_id=200 LIMIT 1), '52:54:00:02:01:01', '192.168.2.1', 'eth1'),
  ((SELECT id FROM virtual_machines WHERE name='VM3' LIMIT 1), (SELECT id FROM networks WHERE vlan_id=200 LIMIT 1), '52:54:00:03:00:01', '192.168.2.2', 'eth0');

-- 7. TAREAS
INSERT INTO tasks (slice_id, vm_id, task_type, status, worker_id, payload)
SELECT
    vm.slice_id,
    vm.id,
    'CREATE_VM',
    'PLACEMENT_READY',
    vm.worker_id,
    jsonb_build_object(
        'vm_name',       vm.name,
        'base_image',    vm.base_image,
        'base_path',     '/mnt/storage/base/',
        'ram',           vm.ram,
        'vcpu',          vm.vcpu,
        'instance_path', COALESCE(vm.instance_path, '/mnt/storage/instances/' || vm.name || '.qcow2'),
        'slice_id',      vm.slice_id,
        'vlan_slice',    (SELECT n.vlan_id FROM networks n WHERE n.slice_id = vm.slice_id ORDER BY n.id LIMIT 1),
        'interfaces',    COALESCE((
            SELECT jsonb_agg(jsonb_build_object(
                'network_id',     vi.network_id,
                'mac_address',    vi.mac_address,
                'ip_address',     vi.ip_address,
                'interface_name', vi.interface_name,
                'tap_name',       COALESCE(vi.tap_name, 'tap-' || vm.name || '-' || vi.interface_name)
            ))
            FROM vm_interfaces vi
            WHERE vi.vm_id = vm.id
        ), '[]'::jsonb)
    )
FROM virtual_machines vm;