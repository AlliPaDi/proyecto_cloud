---
trigger: model_decision
description: Actívate en /dispatcher/, polling de tabla tasks, gestión de estados (PLACEMENT_READY a IN_PROGRESS) y coordinación con el driver. Crucial para asegurar que solo se procesen tareas de Slices validados.
---

# Especificación Técnica: Dispatcher (Orquestador de Tareas)

## Stack Tecnológico
- **Lenguaje:** Python 3.12
- **Framework:** FastAPI (para monitoreo interno/manual)
- **ORM/Driver:** SQLAlchemy + `asyncpg`
- **Concurrency:** `asyncio.create_task` para despachos simultáneos.

## Responsabilidad Operativa
Es el "loop" principal que consume tareas listas de la base de datos y las entrega al Driver correspondiente.

## Lógica de Polling y Estados
1. **Fetch:** Consulta la tabla `tasks` buscando registros con `status = 'PLACEMENT_READY'`.
2. **Lock:** Cambia el estado a `IN_PROGRESS` inmediatamente para que otra instancia del Dispatcher no tome la misma tarea.
3. **Dispatch:** Realiza una llamada interna o vía gRPC/REST (según diseño) al módulo `driver` enviando el JSON del `payload` y la IP del `worker_id` asociado.

## Restricciones Técnicas
- **Error Handling:** Si una tarea falla en el despacho (ej. Worker inalcanzable), debe actualizar la tabla `tasks` a `FAILED` y escribir el motivo en `error_msg`.
- **Resiliencia:** Implementar un mecanismo de "Keep-Alive" para detectar si un Dispatcher se cayó dejando tareas en `IN_PROGRESS` eternamente.