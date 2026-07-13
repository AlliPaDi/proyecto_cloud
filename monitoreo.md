# Requerimientos de Desarrollo: Módulo de Monitoreo de Recursos e Inventario de Servidores (Ex2)

## Objetivo
Implementar una interfaz gráfica (UI) y su lógica asociada para **visualizar de forma independiente el inventario de servidores físicos (recursos disponibles)** de ambas plataformas (Linux Cluster y OpenStack) y **monitorear en tiempo real el consumo de recursos utilizados frente a los asignados**, cumpliendo con la regla de negocio de que el consumo real debe graficarse de forma comparativa respecto al límite asignado.

---

## 1. Interfaz de Usuario (Frontend / UI)

El módulo de Monitoreo debe estar dividido en dos secciones principales o pestañas conmutables: **"Linux Cluster"** y **"OpenStack Cluster"**.

### A. Listado de Recursos / Servidores Disponibles (Independiente del Despliegue)
* **Propósito:** Mostrar la infraestructura física disponible antes o independientemente de que existan máquinas virtuales corriendo.
* **Componentes visuales:**
  * **Para Linux Cluster:** Una tabla o tarjetas fijas que listen los nodos físicos: `server1`, `server2` y `server3`.
  * **Para OpenStack Cluster:** Una tabla o tarjetas fijas que listen los nodos de computación (workers): `worker1`, `worker2` y `worker3`.
  * Cada servidor físico en la lista debe mostrar su capacidad total de hardware de fábrica (Total Cores / Total RAM).

### B. Panel de Consumo en Tiempo Real (Métricas Asignadas vs. Utilizadas)
Para cada servidor listado, la UI debe incorporar elementos gráficos (barras de progreso emparejadas, medidores tipo *gauge* o gráficos de líneas) que permitan contrastar visualmente la métrica de asignación contra el uso real:

1. **Recursos Asignados (Límite Lógico):** Cantidad de Cores y RAM comprometidos para las VMs creadas en ese host (por ejemplo, si hay 2 VMs de 1GB RAM, el recurso asignado es 2GB).
2. **Recursos Utilizados (Consumo Físico Real):** Telemetría en tiempo real del uso de CPU y RAM provista por el backend.
3. **Regla de Diseño (Rúbrica):** Los componentes visuales deben resaltar la relación matemática donde el **recurso utilizado es menor (o igual) al asignado**, permitiendo ver claramente el impacto cuando se ejecute la prueba de carga con `stress-ng` (escalada hasta el 80% del límite asignado).

---

## 2. Requerimientos de Integración y Backend (Referencia para Lógica)

* **Endpoints de Telemetría:** El Frontend consumirá un endpoint (ej. `/api/monitoring/metrics`) que devuelva de forma periódica (cada 3 a 5 segundos) un payload estructurado con la información de los clústeres.
* **Estructura de Datos Esperada (JSON de ejemplo):**
```json
{
  "cluster_type": "OpenStack",
  "nodes": [
    {
      "node_name": "worker1",
      "hardware_total": { "cores": 8, "ram_gb": 16 },
      "resources_assigned": { "cores": 2, "ram_gb": 2 },
      "resources_utilized": { "cores": 1.6, "ram_gb": 1.59 } 
    }
  ]
}
Simulación / Mocking para Pruebas: Si los agentes de monitoreo (como Prometheus, Telegraf o comandos ssh/libvirt nativos del backend) no están conectados aún, la UI debe ser capaz de procesar estos datos mediante un mock para validar que los gráficos aumenten fluidamente cuando el consumo escalado roce el 80% de la cuota asignada.

3. Criterios de Aceptación para la UI (Rúbrica de Evaluación)
[ ] Independencia: La lista de servidores (server2-4 y worker1-3) carga y se muestra correctamente incluso si no hay ningún slice o topología creada en el sistema.

[ ] Visualización del Consumo: Cada recurso posee un indicador visual explícito que separa el hardware lógico asignado del consumo de procesamiento real de la máquina física.

[ ] Capacidad de Escala: Los gráficos de consumo real responden visualmente sin retrasos críticos y soportan la visualización del estrés masivo provocado por procesos concurrentes del sistema.