---
trigger: model_decision
description: Actívate en /slice-manager/ para gestionar el ciclo de vida de Slices y topologías. Coordina la persistencia inicial en PENDING_APPROVAL (solicitud del alumno) y la generación de tareas en tasks tras la aprobación del Slice Admin.
---

# Especificación Técnica: Slice Manager (Business Logic)

## Stack Tecnológico
- **Lenguaje:** Python 3.12
- **Framework:** FastAPI
- **Persistencia:** SQLAlchemy + `asyncpg` (Tablas `slices`, `tasks`, `virtual_machines`)

## Flujo de Trabajo y Jerarquía
1. **Solicitud (Student):** Al recibir un JSON de topología, inserta los registros en `slices`, `virtual_machines` y `networks` con estado `PENDING_APPROVAL`.
2. **Validación (Slice Admin):** Provee endpoints para que el administrador monitoree y apruebe las solicitudes de sus alumnos asignados.
3. **Despliegue (Post-Aprobación):** Una vez validado, el módulo descompone el slice e inserta las tareas individuales en la tabla `tasks` con estado `PENDING`.

## Coordinación de Módulos
- Consulta síncronamente al **Image Manager** para validar imágenes base antes de registrar la solicitud.
- **Post-Aprobación:** Solicita al **Networking** la reserva de Vlan-Slice, cálculo de Vlan-Inner y clasificación de enlaces (local/remoto) **después del Placement**, ya que el Networking necesita el mapa `{vm_id: worker_id}` para saber si un enlace es local o remoto.

## Restricciones
- **RBAC:** Rechazar cualquier intento de aprobación de slice si el rol del usuario no es `SLICE_ADMIN` o `SYSTEM_ADMIN`.
- **Integridad:** Asegurar que el borrado de un slice gatille un `DELETE CASCADE` o una tarea de limpieza en los workers.