---
trigger: always_on
---

# Reglas Globales del Orquestador Cloud - G1

Estándares arquitectónicos críticos para todos los agentes y desarrolladores del repositorio.

## 1. Arquitectura Asíncrona (Async-State Transition)
- Las comunicaciones de estado se realizan vía base de datos SQL en la tabla `tasks`.
- **Flujo de Aprobación:** Las solicitudes de Slices inician en `PENDING_APPROVAL` en las tablas `slices`, `virtual_machines` y `networks`. Solo tras la aprobación del `SLICE_ADMIN` se insertan tareas en la tabla `tasks`.
- **Transición de Tareas (estricta):** `PENDING` -> `PLACEMENT_READY` -> `IN_PROGRESS` -> `READY` o `FAILED`.

## 2. Virtualización y Almacenamiento (Server 4)
- **Captura de PID:** Obligatorio flag `-pidfile /tmp/{vm_name}.pid`.
- **Shared Storage:** Almacenamiento centralizado en el **Server 4** montado vía NFS. Rutas canónicas:
  - Imágenes base: `/mnt/storage/base/`
  - Discos de instancia: `/mnt/storage/instances/`
- **Thin Provisioning:** PROHIBIDO copiar imágenes. Usar `qemu-img create -f qcow2 -b {base_img} {inst_img}` para aprovechar el Copy-on-Write.

## 3. Networking e IPAM (ens4)
- **Red de Datos:** Uso exclusivo de `ens4` como Trunk en el `Br-WK` (bridge de transporte por Worker).
- **Modelo de 3 capas (ver `docs/context/05_Logica_Consistencia_L2.md`):**
  - **Br-Slice** (`br-sl-{slice_id}`): Un bridge por Slice por Worker. Aquí aterrizan los TAPs con etiqueta `Vlan-Inner`.
  - **Vlan-Inner**: Identifica cada enlace lógico dentro del Br-Slice (local al bridge, reutilizable entre Slices).
  - **Vlan-Slice**: Etiqueta de transporte inter-worker (una por Slice, del `vlan_pool` 100-1000). Se aplica en el Br-WK.
- **IPAM:** Cada red del slice recibe un `subnet_cidr` y cada interfaz de VM recibe una `ip_address` asignada por el módulo de Networking.
- **Gestión:** Prohibido alterar la interfaz `ens3` (Management) en los Workers.

## 4. Jerarquía de Roles
- **STUDENT:** Solicita slices (estado inicial `PENDING_APPROVAL`).
- **SLICE_ADMIN:** Valida solicitudes de alumnos y monitorea sus recursos asignados.
- **SYSTEM_ADMIN:** Control total de infraestructura e imágenes base.