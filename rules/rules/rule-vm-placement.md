---
trigger: model_decision
description: Actívate en /vm-placement/. Implementa la asignación cíclica (Round Robin) de VMs a Workers (S1 -> S2 -> S3). Debe validar disponibilidad de recursos antes de confirmar la ubicación y actualizar la tarea a PLACEMENT_READY.
---

# Especificación Técnica: VM Placement (Round Robin Scheduler)

## Stack Tecnológico
- **Lenguaje:** Python 3.12
- **Framework:** FastAPI
- **Persistencia:** SQLAlchemy + `asyncpg` (Tablas `workers`, `tasks`, `config`)

## Responsabilidad Operativa
Asignar un nodo físico a cada VM siguiendo un orden cíclico, asegurando una distribución equitativa entre los servidores del clúster.

## Algoritmo de Ubicación (Round Robin + Resource Check)
1. **Identificación de Secuencia:** El módulo debe mantener un puntero (en la BD o caché) del último `worker_id` utilizado.
2. **Selección Cíclica:** Al procesar una tarea `PENDING`, selecciona el siguiente Worker en la lista (S1 -> S2 -> S3 -> S1...).
3. **Validación de Capacidad:** - Antes de asignar, verifica que el Worker seleccionado esté `ALIVE`.
    - Valida que el Worker tenga RAM y CPU suficiente para la VM. Si el Worker está saturado (>80% de uso), salta al siguiente en la secuencia.
4. **Confirmación:** Actualiza la tarea a `PLACEMENT_READY`, inyectando el `worker_id` y restando los recursos del inventario del Worker en la BD.

## Restricciones Técnicas
- **Persistencia del Puntero:** El estado del Round Robin debe persistirse en una tabla de configuración para que, si el microservicio se reinicia, no empiece siempre desde el Worker 1.
- **Cuotas de Slice:** Debe verificar que el `Slice` asociado a la tarea no exceda sus límites globales comparando con `quota_cpu` y `quota_ram` de la tabla `users` antes de proceder con el Placement.