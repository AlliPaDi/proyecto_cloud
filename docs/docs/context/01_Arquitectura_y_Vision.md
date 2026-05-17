# 01. Arquitectura y Visión: PUCP Private Cloud Orchestrator

## 1. Visión y Jerarquía de Roles
El sistema automatiza topologías de red en capa 2 con una gobernanza de tres niveles:
- **STUDENT:** Solicita la creación de Slices y gestiona sus propias VMs.
- **SLICE_ADMIN:** Valida o rechaza solicitudes de sus alumnos asignados y monitorea sus recursos.
- **SYSTEM_ADMIN:** Vista global de infraestructura, catálogo de imágenes y logs operativos.

## 2. Arquitectura Modular y Persistencia
El sistema es una malla de microservicios (FastAPI) comunicados asíncronamente mediante una tabla de `tasks` en PostgreSQL.
- **Control Plane (Server 4):** Aloja el API Gateway, Auth, Slice Manager, Image Manager, Networking, Placement y Monitoring.
- **Data Plane (Server 1-3):** Nodos Workers que ejecutan las cargas mediante QEMU/KVM y OvS.

## 3. Estrategia de Almacenamiento Centralizado
A diferencia de modelos descentralizados, el **Server 4** actúa como el repositorio NFS compartido. Todos los Workers acceden a la misma ruta de imágenes base y escriben los discos de instancia en el mismo volumen central, facilitando la movilidad y consistencia de los datos.