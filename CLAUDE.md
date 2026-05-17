# CLAUDE.md — PUCP Private Cloud Orchestrator (G1)

## Visión del Proyecto

Sistema que automatiza el despliegue de topologías de red Layer-2 sobre infraestructura física QEMU/KVM + Open vSwitch. Los usuarios diseñan topologías, un administrador las aprueba, y el sistema las despliega automáticamente sobre Workers físicos.

**Jerarquía de roles:**
- `STUDENT` — solicita slices, gestiona sus VMs
- `SLICE_ADMIN` — aprueba/rechaza slices de sus alumnos asignados
- `SYSTEM_ADMIN` — vista global de infraestructura, catálogo de imágenes, logs

---

## Arquitectura de Microservicios

Todos los servicios son **Python 3.12 + FastAPI**. Comunicación asíncrona vía tabla `tasks` en PostgreSQL.

| Módulo | Puerto | Responsabilidad |
|:---|:---|:---|
| `api-gateway` | 8080 | Proxy reverso, validación JWT, inyección de headers |
| `auth` | 8081 | Login, registro, emisión y verificación de JWT |
| `slice-manager` | 8082 | Ciclo de vida de slices y topologías |
| `image-manager` | 8083 | Catálogo de imágenes base `.qcow2` |
| `monitoring` | 8084 | Salud de Workers, métricas por rol |
| `networking` | 8085 | IPAM, VLAN allocation, generación de comandos OVS/NAT |
| `vm-placement` | 8086 | Round Robin Scheduler sobre Workers S1-S3 |
| `dispatcher` | 8087 | Loop de polling: consume `PLACEMENT_READY` → despacha al Driver |
| `driver` | 8088 | Ejecución SSH en Workers: QEMU + OvS + OpenFlow + NAT |

**Stack común:** SQLAlchemy + `asyncpg`, ORM async hacia PostgreSQL.

---

## Infraestructura Física (VNRT)

| Hostname | IP (ens3) | Puerto SSH | Rol |
|:---|:---|:---|:---|
| server1 | 10.0.10.1 | 5801 | Worker 1 (cómputo) |
| server2 | 10.0.10.2 | 5802 | Worker 2 (cómputo) |
| server3 | 10.0.10.3 | 5803 | Worker 3 (cómputo) |
| server4 | 10.0.10.4 | 5804 | HeadNode — Control Plane + NFS |
| OFS | 10.0.10.5 | 5811 | OpenFlow Switch (fabric L2) — solo lectura |
| gateway | 10.0.10.100 | — | NAT/Internet — solo lectura |

**Credenciales Workers:** usuario `ubuntu`, password `ubuntu`. Server4 accede a Workers 1-3 por SSH sin contraseña (llave RSA/ED25519 pre-configurada).

**Redes:**
- `ens3` — Management (10.0.10.0/24): tráfico SSH y microservicios. **NUNCA modificar ni agregar bridges aquí.**
- `ens4` — Data Plane: tráfico de VMs. Configurada como puerto Trunk en `br-wk`.

**Almacenamiento NFS (montado en todos los Workers):**
- Imágenes base: `/mnt/storage/base/`
- Discos de instancia: `/mnt/storage/instances/`

---

## Reglas Globales Críticas (Hard Rules)

Estas reglas aplican a **todos los módulos** sin excepción:

1. **Thin Provisioning obligatorio:** Jamás copiar imágenes base. Siempre usar backing files:
   ```bash
   qemu-img create -f qcow2 -b {base_path} {instance_path}
   ```

2. **Captura de PID obligatoria:** Todo proceso QEMU debe lanzarse con:
   ```bash
   -pidfile /tmp/{vm_name}.pid
   ```

3. **Prohibido tocar `ens3`:** Ningún módulo debe alterar la interfaz de Management en ningún Worker.

4. **Gateway y OFS son Caja Negra:** No conectarse por SSH al Gateway (10.0.10.100) ni al OFS (10.0.10.5).

5. **Transiciones de estado atómicas:** `PENDING` → `PLACEMENT_READY` → `IN_PROGRESS` → `READY` | `FAILED`. No saltar estados.

6. **Flujo de aprobación:** Las solicitudes de Slice nacen como `PENDING_APPROVAL` en `slices`, `virtual_machines` y `networks`. Las tareas en `tasks` **solo se crean tras la aprobación del SLICE_ADMIN**.

7. **Inmutabilidad de imágenes base:** Las imágenes en `/mnt/storage/base/` son de solo lectura. Nunca sobrescribir ni borrarlas.

8. **Seguridad intra-slice vía OpenFlow:** El tráfico VM↔VM dentro del `Br-Slice` no pasa por el kernel. El enforcement es con `ovs-ofctl`, **no con `iptables`**.

9. **NAT solo por `ens4`:** Los comandos `iptables MASQUERADE` para salida a Internet siempre usan `ens4` como interfaz de salida. Nunca `ens3`.

---

## Modelo de Red L2 (Br-Slice / Vlan-Inner / Vlan-Slice)

Ver `docs/docs/context/05_Logica_Consistencia_L2.md` para la referencia completa.

| Concepto | Alcance | Función |
|:---|:---|:---|
| `br-sl-{slice_id}` (Br-Slice) | Por Slice, por Worker | Dominio privado del usuario. Aquí aterrizan los TAPs. |
| Vlan-Inner | Local al Br-Slice | Identifica cada enlace lógico. Reutilizable entre Slices distintos. |
| `br-wk` (Br-WK) | Por Worker (permanente) | Bridge de transporte. Conecta Br-Slices con `ens4`. |
| Vlan-Slice | Global (pool 100-1000) | Etiqueta de transporte inter-worker. Una por Slice. |

**Regla de coherencia:** Una `Vlan-Inner 100` en `Br-Slice-A` es invisible para `Br-Slice-B`. El aislamiento multi-tenant lo garantiza el `Vlan-Slice` en el `Br-WK`.

**Clasificación de enlaces:**
- **Local:** Ambas VMs en el mismo Worker → conexión directa en el Br-Slice.
- **Remoto:** VMs en Workers distintos → patch-ports + Q-in-Q (double tagging).

**Secuencia de comandos OVS para un enlace remoto:**
```bash
# En cada Worker con VMs del Slice:
ovs-vsctl --may-exist add-br br-wk
ovs-vsctl --may-exist add-port br-wk ens4
ovs-vsctl --may-exist add-br br-sl-{slice_id}

# TAPs con Vlan-Inner
ovs-vsctl add-port br-sl-{slice_id} {tap_name} tag={vlan_inner}

# Patch-ports para enlaces remotos (tag=Vlan-Slice en el lado Br-WK)
ovs-vsctl add-port br-sl-{slice_id} patch-to-wk-{slice_id} \
  -- set interface patch-to-wk-{slice_id} type=patch options:peer=patch-to-sl-{slice_id}
ovs-vsctl add-port br-wk patch-to-sl-{slice_id} tag={vlan_slice} \
  -- set interface patch-to-sl-{slice_id} type=patch options:peer=patch-to-wk-{slice_id}
```

**`br-wk` es permanente:** Se crea al inicializar el Worker y **nunca se borra** al eliminar slices.

---

## Flujo de Despliegue End-to-End

```
STUDENT  →  POST /slices/  →  Slice Manager
              ↓ inserta: slices + virtual_machines + networks (PENDING_APPROVAL)

SLICE_ADMIN  →  POST /slices/{id}/approve  →  Slice Manager
              ↓ consulta VM Placement (Round Robin → asigna worker_id)
              ↓ consulta Networking (reserva Vlan-Slice, calcula Vlan-Inner, IPAM)
              ↓ inserta tareas en tasks (PENDING, una por VM)

Dispatcher  →  polling tasks WHERE status='PLACEMENT_READY'
              ↓ cambia a IN_PROGRESS (lock atómico)
              ↓ POST /driver/execute con payload completo

Driver  →  SSH al Worker
              ↓ crea disco qcow2 (Thin Provisioning)
              ↓ crea/configura OvS (Br-WK, Br-Slice, TAPs, patch-ports)
              ↓ lanza QEMU con -pidfile
              ↓ aplica OpenFlow (setup_flows + policy_flows)
              ↓ aplica NAT si internet_access=TRUE
              ↓ actualiza tasks → READY, vm → process_id + vnc_port

Slice Manager  →  cuando todas las tasks del slice están en READY
              ↓ actualiza slices.status → ACTIVE
```

**Rollback:** Si el Driver falla en cualquier punto: SIGTERM al proceso QEMU, borrar TAPs, borrar disco de instancia, borrar patch-ports, borrar `br-sl-{slice_id}` si queda vacío, marcar tarea como `FAILED`.

**Borrado de Slice (DELETE /slices/{id}):**
1. Terminar procesos QEMU por `process_id`
2. Borrar discos `.qcow2` de instancia (nunca las imágenes base)
3. Borrar TAPs y patch-ports del `br-sl-{slice_id}`
4. Borrar `br-sl-{slice_id}` si ya no tiene puertos
5. Borrar archivos `.pid` en `/tmp/`
6. Liberar `vlan_slice` en `vlan_pool` → `AVAILABLE`
7. `DELETE CASCADE` desde `slices`

---

## Schema de Base de Datos

Fuente de verdad: `db/init_schema.sql`.

| Tabla | Propósito |
|:---|:---|
| `users` | Usuarios con roles y cuotas (quota_ram MB, quota_cpu cores) |
| `workers` | Workers S1-S3: recursos totales/disponibles, status ALIVE/DOWN |
| `vlan_pool` | Pool de VLANs 100-1000, status AVAILABLE/USED |
| `slices` | Topologías de usuarios. `vlan_slice` FK a `vlan_pool` |
| `virtual_machines` | VMs: `worker_id`, `process_id`, `vnc_port`, `instance_path` |
| `networks` | Enlaces lógicos: `vlan_inner`, `subnet_cidr`, `is_remote`, `internet_access` |
| `vm_interfaces` | "Cables virtuales": `tap_name`, `mac_address`, `ip_address`, `interface_name` |
| `tasks` | Buffer de trabajo async: `task_type`, `status`, `payload` JSONB |
| `security_rules` | Reglas OpenFlow entre VMs: protocolo, puertos, ALLOW/DENY |
| `config` | Estado persistente clave-valor (ej. puntero Round Robin) |

**Cascades:** `virtual_machines`, `networks`, `tasks`, `vm_interfaces`, `security_rules` tienen `ON DELETE CASCADE` desde `slices`.

---

## Esquema `tasks.payload` (JSONB)

### CREATE_VM (Slice Manager → Dispatcher → Driver)
```json
{
  "vm_name": "VM1",
  "base_image": "ubuntu-22.04.qcow2",
  "base_path": "/mnt/storage/base/ubuntu-22.04.qcow2",
  "instance_path": "/mnt/storage/instances/1.qcow2",
  "ram": 512, "vcpu": 1,
  "slice_id": 1, "vlan_slice": 150,
  "bridge_name": "br-sl-1",
  "interfaces": [
    {"interface_name":"eth0","tap_name":"tap-vm1-eth0","vlan_inner":200,
     "ip_address":"192.168.2.1","mac_address":"52:54:00:01:00:01",
     "network_id":2,"is_remote":true},
    {"interface_name":"eth1","tap_name":"tap-vm1-eth1","vlan_inner":0,
     "ip_address":"192.168.1.1","mac_address":"52:54:00:01:01:01",
     "network_id":1,"is_remote":false}
  ]
}
```

### DELETE_VM
```json
{
  "vm_name": "VM1",
  "instance_path": "/mnt/storage/instances/1.qcow2",
  "process_id": 12345,
  "slice_id": 1, "bridge_name": "br-sl-1", "vlan_slice": 150,
  "worker_ip": "10.0.10.1",
  "interfaces": [{"tap_name":"tap-vm1-eth0","is_remote":true}]
}
```

### APPLY_SECURITY
```json
{
  "slice_id": 1, "bridge_name": "br-sl-1",
  "setup_flows": [
    {"bridge":"br-sl-1","flow":"priority=10,arp,actions=normal"},
    {"bridge":"br-sl-1","flow":"priority=1,ip,actions=drop"}
  ],
  "policy_flows": [
    {"bridge":"br-sl-1","flow":"priority=100,tcp,...,actions=normal"}
  ]
}
```

---

## Reglas por Módulo

### API Gateway (8080)
- Stateless: no guarda sesiones.
- Decodifica JWT con PyJWT (solo lectura). Inyecta `X-User-Id` y `X-User-Role` en cada request reenviado.
- Límite de payload: 2 MB.
- Rutas públicas: solo `/api/v1/auth/*`. Todo lo demás requiere token válido.
- `/api/v1/infra/*` y `/api/v1/networking/*` restringidos a `SYSTEM_ADMIN`.

### Auth (8081)
- Único módulo que escribe en `users`.
- Contraseñas con Bcrypt 12 rondas.
- JWT claims: `sub` (user_id), `username`, `role`, `exp`.
- `STUDENT` requiere `admin_id` apuntando a un `SLICE_ADMIN` activo.

### Slice Manager (8082)
- Valida imagen con Image Manager antes de registrar la solicitud.
- Llama a VM Placement **antes** de llamar a Networking (Networking necesita el mapa `{vm_id: worker_id}` para clasificar enlaces local/remoto).
- RBAC estricto: solo `SLICE_ADMIN` o `SYSTEM_ADMIN` pueden aprobar slices.

### Image Manager (8083)
- Valida existencia en `/mnt/storage/base/`.
- Bloquea path traversal en nombres de imagen.
- Define ruta de instancia: `/mnt/storage/instances/{vm_id}.qcow2`.

### Monitoring (8084)
- Actualiza `workers.current_cpu_load` y `workers.current_ram_available` periódicamente.
- Si un Worker no reporta → estado `DOWN` → VM Placement lo salta en Round Robin.
- Visibilidad filtrada por rol: STUDENT ve solo sus VMs, SLICE_ADMIN ve sus alumnos, SYSTEM_ADMIN ve todo.
- No saturar `ens3` con polling excesivo.

### Networking (8085)
- **Solo planifica, nunca ejecuta** comandos en Workers.
- Reserva una `Vlan-Slice` del pool (100-1000) por Slice.
- Asigna `Vlan-Inner` por enlace (local al Br-Slice, no usa el pool global).
- Clasifica enlaces en `is_remote` tras recibir el mapa de placement.
- Endpoints auxiliares (solo generan instrucciones, no ejecutan):
  - `GET /networking/ovs/commands/{slice_id}` — comandos `ovs-vsctl` para el Driver
  - `GET /networking/security/flows/{slice_id}` — reglas OpenFlow
  - `GET /networking/nat/commands/{slice_id}` — comandos `iptables`

### VM Placement (8086)
- Round Robin: S1 → S2 → S3 → S1... El puntero `last_worker_id` persiste en tabla `config`.
- Antes de asignar: verifica `status='ALIVE'` y recursos disponibles (salta Worker si uso > 80%).
- Valida cuotas del usuario (`quota_ram`, `quota_cpu`) antes del placement.
- Al confirmar: actualiza tarea a `PLACEMENT_READY` e inyecta `worker_id`.

### Dispatcher (8087)
- Loop: busca `tasks WHERE status='PLACEMENT_READY'` → cambia a `IN_PROGRESS` → llama al Driver.
- Lock atómico al cambiar estado para evitar doble despacho.
- Si el despacho falla → marca tarea `FAILED` con motivo en `error_msg`.
- Detectar tareas bloqueadas en `IN_PROGRESS` (Keep-Alive / timeout).

### Driver (8088)
- Única capa que ejecuta comandos reales en Workers vía AsyncSSH.
- Puede operar en **modo asistido**: consume `GET /networking/ovs/commands/{slice_id}` y ejecuta la lista pre-calculada.
- Operaciones obligatorias para CREATE_VM:
  1. `qemu-img create -f qcow2 -b {base} {instancia}` (Thin Provisioning)
  2. `ovs-vsctl --may-exist add-br br-wk` + trunk `ens4`
  3. `ovs-vsctl --may-exist add-br br-sl-{slice_id}`
  4. TAPs con `tag={vlan_inner}` en Br-Slice
  5. Patch-ports si `is_remote=TRUE` con `tag={vlan_slice}` en Br-WK
  6. Lanzar QEMU con `-pidfile /tmp/{vm_name}.pid -daemonize`
  7. Aplicar OpenFlow: `ovs-ofctl add-flow`
  8. Aplicar NAT si `internet_access=TRUE`: `iptables MASQUERADE` por `ens4`
- Al finalizar: leer PID, detectar VNC port, actualizar `virtual_machines` y tarea → `READY`.
- **NUNCA borrar** `br-wk` ni `ens4`.

---

## Desarrollo Local

### Requisitos previos
- Docker Desktop (para PostgreSQL)
- Python 3.12
- Cada módulo tiene su propio `.venv` **dentro de su carpeta**

### Levantar la base de datos
```bash
docker-compose up -d postgres
docker exec -it orchestrator-db psql -U orchestrator -d orchestrator_db -c "\dt"
# Seed de prueba completo:
docker exec -i orchestrator-db psql -U orchestrator -d orchestrator_db < db/seeds/full_pipeline_seed.sql
```

### Levantar un módulo individualmente
```bash
cd auth/
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
uvicorn main:app --reload --port 8081
```

### Variables de entorno clave

| Variable | Default | Módulos |
|:---|:---|:---|
| `DATABASE_URL` | `postgresql+asyncpg://orchestrator:orchestrator@localhost:5432/orchestrator_db` | Todos excepto API Gateway |
| `JWT_SECRET` | `dev-secret-key` | Auth, API Gateway |
| `JWT_ALGORITHM` | `HS256` | Auth, API Gateway |
| `SSH_ENABLED` | `false` | Monitoring, Driver |
| `IMAGE_BASE_PATH` | `/mnt/storage/base/` | Image Manager |

Copiar `.env.example` a `.env` y ajustar si es necesario.

### Levantar todo el stack
```bash
docker-compose up --build
```

---

## Convenciones Git

**Branches:**
```
feature/auth-login
feature/networking-vlan-allocation
fix/driver-rollback-cleanup
```

**Commits:**
```
[auth] feat: implement JWT login endpoint
[networking] fix: vlan_inner assignment for local links
[db] chore: add cascade delete to vm_interfaces
```

**Pull Requests:** siempre contra `main`. Incluir qué módulo se modifica, endpoints nuevos/cambiados y si se modificó `docker-compose.yml`.

---

## Archivos de Referencia

| Archivo | Cuándo consultarlo |
|:---|:---|
| `docs/docs/context/05_Logica_Consistencia_L2.md` | Al trabajar en Networking o Driver |
| `docs/docs/modules/{modulo}_contract.md` | Siempre: define inputs/outputs del módulo |
| `docs/docs/modules/payload_schema.md` | Al escribir o leer `tasks.payload` |
| `db/init_schema.sql` | Siempre: contrato universal de datos |
| `rules/rules/rule-{modulo}.md` | Siempre: restricciones específicas del módulo |
| `rules/rules/global_orchestrator_rules.md` | Al definir cualquier comportamiento arquitectónico |
