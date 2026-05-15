---
trigger: model_decision
description: Actívate en /monitoring/, dashboards de Grafana, Prometheus o salud de Workers. Define métricas de CPU/RAM, heartbeats y computed columns para normalización. Filtra visibilidad por roles STUDENT/SLICE_ADMIN/SYSTEM_ADMIN.
---

# Especificación Técnica: Módulo Monitoring (Observability)

## Stack Tecnológico
- **Lenguaje:** Python 3.12
- **Framework:** FastAPI
- **Recolección:** Prometheus Client / Telegraf (Agente ligero en Workers).
- **Visualización:** Grafana (conector PostgreSQL/Prometheus).
- **Persistencia:** SQLAlchemy + `asyncpg` (Actualización de tabla `workers`).

## Responsabilidad Operativa
Garantizar la visibilidad del estado de salud del clúster y la telemetría de las cargas de trabajo de forma segmentada por roles.

## Lógica de Telemetría y Salud
1. **Heartbeat & Load:** Debe recibir o consultar periódicamente el estado de los Workers (S1, S2, S3). Actualiza `current_cpu_load` y `current_ram_available` en la tabla `workers`.
2. **Estado de Nodo:** Si un Worker no reporta en X segundos, cambia su estado a `DOWN`. Esto gatilla que el **VM-Placement** lo salte en la secuencia de Round Robin.
3. **Normalización:** Para los dashboards de red o sensores, se prohíbe el procesamiento pesado en el backend; se debe delegar a **Computed Columns** en SQL o transformaciones en Grafana.

## Visibilidad Jerárquica (RBAC)
- **STUDENT:** Solo puede ver métricas de sus VMs activas mediante el dashboard filtrado por su `user_id`.
- **SLICE_ADMIN:** Vista agregada del consumo de recursos de todos los Slices de sus alumnos asignados.
- **SYSTEM_ADMIN:** Acceso total a las métricas de infraestructura física, estado de los puentes OvS y salud del Headnode (Server 4).

## Restricciones Técnicas
- **Latencia:** El polling de métricas no debe saturar la red de gestión `ens3`.
- **Alertas:** Debe exponer un endpoint de `/health` para que el API Gateway pueda realizar self-healing si un microservicio se detiene.