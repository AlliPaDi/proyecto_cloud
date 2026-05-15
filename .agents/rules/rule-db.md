---
trigger: model_decision
description: Actívate en /db/, modificaciones a init_schema.sql, diseño de modelos de datos o lógica de persistencia. Define el flujo de estados PENDING_APPROVAL -> PENDING -> READY y la integridad de las tablas tasks y slices.
---

# Reglas del Módulo: Database (Persistence & Task Buffer)

Este módulo define la estructura de datos y el flujo de estados que permite la operación asíncrona del orquestador.

## 1. Flujo de Persistencia Obligatorio (Rethinked Flow)
- **Fase de Solicitud:** Al recibir un JSON de topología, se debe insertar inmediatamente en las tablas `slices`, `virtual_machines` y `networks` con estado `PENDING_APPROVAL`.
- **Fase de Aprobación:** Solo cuando el `SLICE_ADMIN` aprueba el slice, se deben generar e insertar los registros en la tabla `tasks` con estado `PENDING` para iniciar el despliegue técnico.

## 2. Integridad de la Tabla `tasks`
- Actúa como el buffer de trabajo. Cada registro debe tener un `task_type` (ej. CREATE_VM) y un `payload` JSONB con los detalles técnicos para el Driver.
- Las transiciones de estado deben ser atómicas: `PENDING` -> `PLACEMENT_READY` -> `IN_PROGRESS` -> `READY` o `FAILED`.

## 3. Topología e IPAM (Modelo Br-Slice / Vlan-Inner / Vlan-Slice)
- **`slices`:** Incluye `vlan_slice` (FK a `vlan_pool`): la etiqueta de transporte inter-worker asignada al Slice completo.
- **`networks` (Links):** Cada enlace lógico almacena un `vlan_inner` (etiqueta local al Br-Slice) y un flag `is_remote` (TRUE si las VMs del enlace están en Workers distintos). El `bridge_name` (`br-sl-{slice_id}`) se deriva del `slice_id`, no se almacena per-link.
- **`vm_interfaces`:** Tabla que vincula VMs con enlaces. Cada registro representa un "cable virtual" con: `ip_address`, `mac_address`, `interface_name` y `tap_name`.
- **Multi-homing:** Una VM intermedia (ej. VM2 en VM1-VM2-VM3) tendrá múltiples registros en `vm_interfaces`, cada uno con un `network_id` distinto (y por tanto distinta `vlan_inner`), pero todos conectados al mismo `br-sl-{slice_id}`.
- **Aislamiento:** Dos Slices distintos pueden reutilizar las mismas `vlan_inner` sin conflicto, porque cada uno tiene su propio Br-Slice aislado. El `vlan_slice` en el Br-WK garantiza la separación en el backbone.

## 4. Estándares Técnicos
- Usar `ON DELETE CASCADE` en tablas dependientes de `slices` para asegurar una limpieza completa de la base de datos al eliminar una topología.
- El campo `updated_at` debe actualizarse automáticamente en cada cambio de estado de una tarea para permitir el monitoreo de timeouts por el Dispatcher.
- El campo `instance_path` en `virtual_machines` almacena la ruta canónica del disco qcow2 en el Shared Storage del Server 4.