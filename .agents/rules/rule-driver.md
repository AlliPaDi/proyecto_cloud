---
trigger: model_decision
description: Actívate en /driver/, comandos QEMU/KVM (-pidfile, qcow2), configuración OvS (ovs-vsctl) e interacción directa con Workers. Implementa la capa física de virtualización y redes.
---

# Especificación Técnica: Driver (Capa de Ejecución)

## Stack Tecnológico
- **Lenguaje:** Python 3.12
- **Comunicación:** `AsyncSSH` (Para ejecución remota en Workers S1, S2, S3).
- **Lógica de comandos:** Scripts de Bash inyectados o comandos directos vía SSH.

## Responsabilidad Operativa
Ejecutor de bajo nivel en los Workers. Es el único módulo que toca el hardware/kernel y gestiona el ciclo de vida de los procesos QEMU y puentes OvS.

## Operaciones Mandatorias (Hard Rules)
- **Virtualización:** - Crear discos usando backing files: `qemu-img create -f qcow2 -b {base} {instancia}`.
    - Lanzar QEMU con `-pidfile /tmp/{vm_name}.pid`.
- **Networking — Modelo Br-Slice / Vlan-Inner (ver `docs/context/05_Logica_Consistencia_L2.md`):**
    1. **Br-WK (una vez por Worker):** Asegurar que exista el bridge de transporte: `ovs-vsctl --may-exist add-br br-wk` con `ens4` como puerto trunk.
    2. **Br-Slice (una vez por Slice por Worker):** Crear el bridge privado del usuario: `ovs-vsctl --may-exist add-br br-sl-{slice_id}`.
    3. **TAPs:** Para cada interfaz de la VM, crear el TAP y conectarlo al Br-Slice con la etiqueta Vlan-Inner del enlace: `ovs-vsctl add-port br-sl-{slice_id} {tap_name} tag={vlan_inner}`.
    4. **Patch Ports (solo enlaces remotos):** Si `is_remote=TRUE`, crear patch-ports bidireccionales entre `br-sl-{slice_id}` y `br-wk`, etiquetando el lado del Br-WK con `tag={vlan_slice}`.
    5. **Prohibido:** Tocar la interfaz `ens3` (Management) o conectar TAPs directamente al `br-wk`.

## Reporte de Éxito y Persistencia
- Leer el archivo `.pid` del Worker y reportar el `process_id` a la tabla `virtual_machines`.
- Detectar el puerto VNC asignado y registrarlo.
- Finalizar actualizando la tarea a `READY`.

## Almacenamiento Compartido
- El disco se crea sobre el Shared Storage NFS del Server 4: `qemu-img create -f qcow2 -b {base_path} {instance_path}`.

## Rollback y Limpieza
- Si una tarea falla o un Slice se elimina, el Driver debe:
    1. Terminar el proceso QEMU (SIGTERM/SIGKILL).
    2. Eliminar los puertos TAP del Br-Slice.
    3. Eliminar los patch-ports hacia el Br-WK.
    4. Borrar el bridge `br-sl-{slice_id}` si ya no tiene puertos activos (no queda ninguna VM del Slice en ese Worker).
    5. **NUNCA borrar** el `br-wk` ni `ens4`.