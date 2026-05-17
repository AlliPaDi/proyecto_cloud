---
trigger: model_decision
description: Actívate en /networking/ al asignar VLANs (rango 100-1000), configurar IPAM, planificar el aislamiento L2 sobre la red de datos ens4, gestionar reglas de seguridad OpenFlow o generar comandos OVS/NAT para el Driver.
---

# Especificación Técnica: Módulo Networking & Security

## Stack Tecnológico
- **Lenguaje:** Python 3.12
- **Framework:** FastAPI
- **Base de Datos:** SQLAlchemy + `asyncpg` (Tablas `vlan_pool`, `networks`, `vm_interfaces`, `security_rules`)

## Responsabilidad Operativa
Actúa como la autoridad de red y seguridad L2/L3 del clúster. Su función es de **planificación, asignación de recursos lógicos y generación de configuraciones**. NO ejecuta comandos directamente en los Workers.

## Lógica de Red L2/L3 — Modelo Br-Slice / Vlan-Inner / Vlan-Slice
- **Vlan-Slice (Transporte):** Reserva **una única VLAN del pool** (100-1000) por Slice. Se persiste en `slices.vlan_slice`. Se usa para el tráfico inter-worker en el Br-WK.
- **Vlan-Inner (Topología):** Asigna una etiqueta local por cada enlace lógico. Se persiste en `networks.vlan_inner`. Es local al Br-Slice (reutilizable entre Slices distintos).
- **Clasificación de Enlaces:** Tras recibir el mapa de placement del Slice Manager, marca cada enlace en `networks.is_remote` como `TRUE` (VMs en Workers distintos) o `FALSE` (mismo Worker).
- **IPAM:** Asigna subredes (`subnet_cidr` en tabla `networks`) e IPs específicas a cada interfaz (`ip_address` en tabla `vm_interfaces`).
- **Referencia:** Ver `docs/context/05_Logica_Consistencia_L2.md` para el flujo completo de Q-in-Q.

## Generación de Comandos OVS (Nuevo)
- Expone un endpoint que **pre-calcula** la lista exacta de comandos `ovs-vsctl` que el Driver debe ejecutar en cada Worker.
- Genera: creación de Br-Slice, TAPs con tags, patch-ports para enlaces remotos y trunk de ens4 en br-wk.
- El Driver consume este endpoint y actúa como ejecutor "tonto", reduciendo la lógica en la capa de ejecución.

## Micro-Segmentación por OpenFlow (Nuevo)
- Gestiona la tabla `security_rules` para definir políticas de tráfico entre VMs dentro de un Slice.
- Genera reglas OpenFlow (compatibles con `ovs-ofctl`) para enforcement directo en el Br-Slice.
- Lógica por defecto: ARP permitido (`priority=10`), todo IP denegado (`priority=1`), las reglas del usuario tienen prioridad intermedia.
- El tráfico VM↔VM dentro del Br-Slice NO pasa por el kernel del host, por lo que `iptables` no aplica — el enforcement es con `ovs-ofctl`.

## NAT / Salida a Internet (Nuevo)
- Redes con `internet_access=TRUE` en la tabla `networks` habilitan salida a Internet.
- Genera comandos `iptables` (MASQUERADE, FORWARD) que el Driver ejecuta en el Worker correspondiente.
- El tráfico VM→Internet SÍ pasa por el kernel del Worker (a diferencia del tráfico intra-Br-Slice).
- La interfaz de salida siempre es `ens4` (red de datos).

## Restricciones Técnicas
- **Aislamiento de Gestión:** Prohibido generar cualquier configuración que afecte a la interfaz `ens3`.
- **Salida de Datos (allocate):** Su respuesta principal es un JSON descriptivo con: `vlan_slice`, `vlan_inner`, `is_remote`, `bridge_name` (derivado: `br-sl-{slice_id}`), `ip_address`, `tap_name` y `mac_address`.
- **Endpoints auxiliares:** Los endpoints de comandos OVS (`/networking/ovs/commands/`), flows de seguridad (`/networking/security/flows/`) y NAT (`/networking/nat/commands/`) generan instrucciones listas para ejecutar, pero el módulo **NO ejecuta** `ovs-vsctl`, `ovs-ofctl` ni `iptables` directamente.