# 03. Flujo de Despliegue de Slices: Protocolo de Aprobación y Ejecución

## Fase 0: Solicitud y Validación Humana
1. **Petición Estudiante:** El `STUDENT` envía el JSON de topología.
2. **Registro en Sombra:** El Slice Manager inserta los datos en las tablas `slices`, `virtual_machines` y `networks` con estado `PENDING_APPROVAL`.
3. **Aprobación:** El `SLICE_ADMIN` revisa la solicitud en su dashboard. Al aprobar, el sistema inserta las entradas correspondientes en la tabla `tasks` con estado `PENDING`.

## Fase 1: Ubicación (Placement)
- El módulo **VM Placement** selecciona el Worker (S1-S3) usando un algoritmo **Round Robin**.
- La tarea transiciona a `PLACEMENT_READY`.

## Fase 2: Ejecución (Driver)
- El **Dispatcher** envía la orden al **Driver** vía `AsyncSSH`.
- El Driver aplica las reglas de **Thin Provisioning** y **Captura de PID** sobre el almacenamiento compartido del Server 4.
- El Driver configura la **IP** de cada interfaz dentro de la VM (cloud-init o inyección estática) usando los datos de `vm_interfaces`.

## Fase 3: Finalización y Manejo de Errores
1. **Éxito (`READY`):** El Driver lee el archivo `.pid` del Worker, registra `process_id` y `vnc_port` en la tabla `virtual_machines`, y actualiza la tarea a `READY`.
2. **Fallo (`FAILED`):** Si algún comando falla, el Driver ejecuta un **Rollback** (limpieza de puertos TAP, archivos `.qcow2` parciales y `.pid` en `/tmp/`) y marca la tarea como `FAILED` con el motivo en `error_msg`.
3. **Actualización de Slice:** Cuando todas las tareas de un slice están en `READY`, el Slice Manager actualiza el slice a estado `ACTIVE`.

## Fase 4: Borrado Inteligente (Cleanup)
Al eliminar un slice:
1. Se terminan los procesos QEMU usando los `process_id` guardados.
2. Se borran los discos `.qcow2` de instancia (NUNCA las imágenes base).
3. Se eliminan los puertos TAP del `br-sl-{slice_id}`.
4. Se eliminan los patch-ports hacia el `br-wk`.
5. Se borra el bridge `br-sl-{slice_id}` si ya no tiene puertos activos.
6. Se borran los archivos `.pid` en `/tmp/`.
7. Se libera el `vlan_slice` marcándolo como `AVAILABLE` en `vlan_pool`.
8. Se ejecuta `DELETE CASCADE` desde la tabla `slices`.