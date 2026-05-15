---
trigger: model_decision
description: Actívate en /networking/ al asignar VLANs (rango 100-1000), configurar IPAM o planificar el aislamiento L2 sobre la red de datos ens4. Define parámetros técnicos para que el Driver configure Open vSwitch sin ejecutar comandos directamente.
---

# Especificación Técnica: Módulo Networking & Security

## Stack Tecnológico
- **Lenguaje:** Python 3.12
- **Framework:** FastAPI
- **Base de Datos:** SQLAlchemy + `asyncpg` (Consulta tabla `vlan_pool`)

## Responsabilidad Operativa
Actúa como la autoridad de red del clúster. Su función es puramente de planificación y asignación de recursos lógicos.

## Lógica de Red L2/L3 — Modelo Br-Slice / Vlan-Inner / Vlan-Slice
- **Vlan-Slice (Transporte):** Reserva **una única VLAN del pool** (100-1000) por Slice. Se persiste en `slices.vlan_slice`. Se usa para el tráfico inter-worker en el Br-WK.
- **Vlan-Inner (Topología):** Asigna una etiqueta local por cada enlace lógico. Se persiste en `networks.vlan_inner`. Es local al Br-Slice (reutilizable entre Slices distintos).
- **Clasificación de Enlaces:** Tras recibir el mapa de placement del Slice Manager, marca cada enlace en `networks.is_remote` como `TRUE` (VMs en Workers distintos) o `FALSE` (mismo Worker).
- **IPAM:** Asigna subredes (`subnet_cidr` en tabla `networks`) e IPs específicas a cada interfaz (`ip_address` en tabla `vm_interfaces`).
- **Referencia:** Ver `docs/context/05_Logica_Consistencia_L2.md` para el flujo completo de Q-in-Q.

## Restricciones Técnicas
- **Aislamiento de Gestión:** Prohibido generar cualquier configuración que afecte a la interfaz `ens3`.
- **Salida de Datos:** Su respuesta debe ser un JSON descriptivo con: `vlan_slice`, `vlan_inner`, `is_remote`, `bridge_name` (derivado: `br-sl-{slice_id}`), `ip_address`, `tap_name` y reglas de firewall. NO ejecuta comandos `ovs-vsctl` o `iptables`.