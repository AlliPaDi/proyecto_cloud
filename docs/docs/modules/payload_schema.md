# Esquema del campo `tasks.payload` (JSONB)

Este documento define el contrato exacto del campo `payload` en la tabla `tasks`. Todos los módulos que escriben o leen este campo **deben** respetar estos esquemas.

---

## CREATE_VM

Escrito por: **Slice Manager** (al aprobar el slice).
Leído por: **Dispatcher** → **Driver**.

```json
{
  "vm_name": "VM1",
  "base_image": "ubuntu-22.04.qcow2",
  "base_path": "/mnt/storage/base/ubuntu-22.04.qcow2",
  "instance_path": "/mnt/storage/instances/1.qcow2",
  "ram": 512,
  "vcpu": 1,
  "slice_id": 1,
  "vlan_slice": 150,
  "bridge_name": "br-sl-1",
  "interfaces": [
    {
      "interface_name": "eth0",
      "tap_name": "tap-vm1-eth0",
      "vlan_inner": 200,
      "ip_address": "192.168.2.1",
      "mac_address": "52:54:00:01:00:01",
      "network_id": 2,
      "is_remote": true
    },
    {
      "interface_name": "eth1",
      "tap_name": "tap-vm1-eth1",
      "vlan_inner": 0,
      "ip_address": "192.168.1.1",
      "mac_address": "52:54:00:01:01:01",
      "network_id": 1,
      "is_remote": false
    }
  ]
}
```

### Campos obligatorios

| Campo | Tipo | Descripción |
|:---|:---|:---|
| `vm_name` | string | Nombre de la VM (único dentro del slice) |
| `base_image` | string | Nombre del archivo .qcow2 base |
| `base_path` | string | Ruta absoluta de la imagen base en el NFS |
| `instance_path` | string | Ruta absoluta del disco de instancia a crear |
| `ram` | int | RAM en MB |
| `vcpu` | int | Número de cores |
| `slice_id` | int | ID del slice al que pertenece |
| `vlan_slice` | int | Vlan-Slice asignada al slice (del pool 100-1000) |
| `bridge_name` | string | Nombre del Br-Slice: `br-sl-{slice_id}` |
| `interfaces` | array | Lista de interfaces de red (ver abajo) |

### Campos de cada interfaz

| Campo | Tipo | Descripción |
|:---|:---|:---|
| `interface_name` | string | Nombre dentro del guest: `eth0`, `eth1`, etc. |
| `tap_name` | string | Nombre del TAP en el host: `tap-vm1-eth0` |
| `vlan_inner` | int | Etiqueta Vlan-Inner (local al Br-Slice) |
| `ip_address` | string | IP asignada por IPAM |
| `mac_address` | string | MAC asignada (formato `52:54:00:xx:xx:xx`) |
| `network_id` | int | FK a `networks.id` para trazabilidad |
| `is_remote` | bool | `true` si el enlace cruza Workers (requiere patch-ports) |
| `internet_access` | bool | `true` si la red tiene salida a Internet (requiere NAT) |

---

## DELETE_VM

Escrito por: **Slice Manager** (al eliminar un slice).
Leído por: **Dispatcher** → **Driver** (para rollback/cleanup).

```json
{
  "vm_name": "VM1",
  "instance_path": "/mnt/storage/instances/1.qcow2",
  "process_id": 12345,
  "slice_id": 1,
  "bridge_name": "br-sl-1",
  "vlan_slice": 150,
  "worker_ip": "10.0.10.1",
  "interfaces": [
    {
      "tap_name": "tap-vm1-eth0",
      "is_remote": true
    },
    {
      "tap_name": "tap-vm1-eth1",
      "is_remote": false
    }
  ]
}
```

### Secuencia de limpieza del Driver
1. `kill {process_id}` (SIGTERM, luego SIGKILL si no responde).
2. `rm {instance_path}` (borrar disco de instancia).
3. `rm /tmp/{vm_name}.pid`.
4. Para cada interfaz: `ovs-vsctl del-port {bridge_name} {tap_name}`.
5. Si `is_remote`: borrar patch-ports entre `{bridge_name}` y `br-wk`.
6. Si el bridge `{bridge_name}` no tiene más puertos: `ovs-vsctl del-br {bridge_name}`.

---

## APPLY_SECURITY

Escrito por: **Slice Manager** (tras despliegue exitoso de todas las VMs del slice, o al actualizar reglas de seguridad).
Leído por: **Dispatcher** → **Driver**.

```json
{
  "slice_id": 1,
  "bridge_name": "br-sl-1",
  "setup_flows": [
    {"bridge": "br-sl-1", "flow": "priority=10,arp,actions=normal"},
    {"bridge": "br-sl-1", "flow": "priority=1,ip,actions=drop"}
  ],
  "policy_flows": [
    {"bridge": "br-sl-1", "flow": "priority=100,tcp,in_port=tap-vm1-eth0,nw_src=192.168.2.1,nw_dst=192.168.2.2,tp_dst=80,actions=normal"}
  ]
}
```

### Campos obligatorios

| Campo | Tipo | Descripción |
|:---|:---|:---|
| `slice_id` | int | ID del slice al que pertenecen las reglas |
| `bridge_name` | string | Nombre del Br-Slice: `br-sl-{slice_id}` |
| `setup_flows` | array | Reglas base: ARP allow + default-deny IP |
| `policy_flows` | array | Reglas del usuario derivadas de `security_rules` |

### Secuencia de aplicación del Driver
1. Para cada flow en `setup_flows`: `ovs-ofctl add-flow {bridge} "{flow}"`.
2. Para cada flow en `policy_flows`: `ovs-ofctl add-flow {bridge} "{flow}"`.
3. Si el Slice tiene redes con `internet_access=TRUE`, el Driver además consume `GET /networking/nat/commands/{slice_id}` y ejecuta los comandos `iptables` retornados.
