# 05. Lógica de Consistencia L2: Modelo Br-Slice / Vlan-Inner / Vlan-Slice

## 1. Jerarquía de Bridges y Etiquetas

El sistema utiliza tres capas de abstracción para garantizar la fidelidad topológica y el aislamiento multi-tenant:

| Concepto | Alcance | Función |
|:---|:---|:---|
| **Br-Slice** (`br-sl-{slice_id}`) | Por Slice, por Worker | Dominio de colisión privado del usuario. Aquí "aterrizan" los TAPs de sus VMs. |
| **Vlan-Inner** | Dentro del Br-Slice | Identifica cada enlace lógico. Dos interfaces solo se ven si comparten la misma Vlan-Inner dentro del mismo Br-Slice. |
| **Br-WK** (`br-wk`) | Por Worker (uno solo) | Bridge de transporte central. Conecta todos los Br-Slice del Worker con la interfaz física `ens4` hacia el OFS. |
| **Vlan-Slice** | Global (pool 100-1000) | Etiqueta de transporte inter-worker. Identifica el Slice en el backbone físico. Asignada una por Slice desde `vlan_pool`. |

### Regla de Coherencia
- Una `Vlan-Inner 100` dentro de `Br-Slice-A` es **invisible** para `Br-Slice-B`, incluso si este último también usa `Vlan-Inner 100`. El aislamiento entre usuarios se garantiza por el `Vlan-Slice` en el `Br-WK`.

---

## 2. Algoritmo General de Despliegue de Red

Dado un Slice con N VMs y M enlaces lógicos, el proceso es:

### Paso 1: Placement (Round Robin)
- El VM Placement asigna cada VM a un Worker (S1, S2 o S3).
- Resultado: mapa `{vm_id: worker_id}`.

### Paso 2: Asignación de Vlan-Slice
- El módulo Networking reserva **una única `Vlan-Slice`** del pool (100-1000) para todo el Slice.
- Esta etiqueta se usa exclusivamente para el transporte inter-worker por el backbone OFS.

### Paso 3: Asignación de Vlan-Inner por enlace
- Para cada enlace lógico (par de interfaces), se asigna una `Vlan-Inner` que es **local al Br-Slice**.
- Las Vlan-Inner NO se toman del `vlan_pool` global; son un contador interno del Slice (ej. 100, 200, 300...) reutilizable entre Slices distintos porque cada Br-Slice es un dominio aislado.

### Paso 4: Clasificación de enlaces
Para cada enlace, el sistema evalúa el mapa de placement:
- **Enlace Local:** Ambas VMs están en el mismo Worker → conexión directa dentro del Br-Slice, sin involucrar al Br-WK.
- **Enlace Remoto:** Las VMs están en Workers distintos → requiere Patch Port al Br-WK y double tagging (Q-in-Q).

### Paso 5: Despliegue por el Driver

#### 5a. En cada Worker donde el Slice tenga VMs:
```bash
# Crear el Br-Slice (idempotente)
ovs-vsctl --may-exist add-br br-sl-{slice_id}

# Crear el TAP para cada VM y conectarlo al Br-Slice
ovs-vsctl add-port br-sl-{slice_id} {tap_name} tag={vlan_inner}
```

#### 5b. Para enlaces remotos (Q-in-Q):
```bash
# En el Worker de ORIGEN:
# 1. Crear Patch Port del Br-Slice al Br-WK
ovs-vsctl add-port br-sl-{slice_id} patch-to-wk-{slice_id} \
  -- set interface patch-to-wk-{slice_id} type=patch options:peer=patch-to-sl-{slice_id}
ovs-vsctl add-port br-wk patch-to-sl-{slice_id} tag={vlan_slice} \
  -- set interface patch-to-sl-{slice_id} type=patch options:peer=patch-to-wk-{slice_id}

# 2. El Br-WK ya debe tener ens4 como puerto trunk:
ovs-vsctl --may-exist add-port br-wk ens4
```

#### 5c. Flujo de paquetes en enlace remoto:
```
VM (eth0) → TAP (tag=Vlan-Inner) → Br-Slice
  → Patch Port → Br-WK (tag=Vlan-Slice)
  → ens4 → OFS → ens4 destino
  → Br-WK destino (strip Vlan-Slice) → Patch Port → Br-Slice destino
  → TAP destino (match Vlan-Inner) → VM destino
```

---

## 3. Ejemplo Concreto: Topología de 6 VMs

### Topología solicitada (ver `TopoEx1.json`):
```
VM1(S1) ---[enlace A]--- VM4(S1)     ← Local (mismo Worker)
VM1(S1) ---[enlace B]--- VM2(S2)     ← Remoto
VM2(S2) ---[enlace C]--- VM3(S3)     ← Remoto
VM3(S3) ---[enlace D]--- VM4(S1)     ← Remoto
VM4(S1) ---[enlace E]--- VM5(S2)     ← Remoto
VM5(S2) ---[enlace F]--- VM6(S3)     ← Remoto
```

### Asignaciones:
| Concepto | Valor |
|:---|:---|
| Vlan-Slice (del pool global) | `150` |
| Enlace A (VM1↔VM4): Vlan-Inner | `0` (untagged, mismo bridge local) |
| Enlace B (VM1↔VM2): Vlan-Inner | `200` |
| Enlace C (VM2↔VM3): Vlan-Inner | `300` |
| Enlace D (VM3↔VM4): Vlan-Inner | `100` |
| Enlace E (VM4↔VM5): Vlan-Inner | `400` |
| Enlace F (VM5↔VM6): Vlan-Inner | `500` |

### Resultado en cada Worker:

**Server 1 (VM1, VM4):**
```
br-sl-{slice_id}:
  ├─ tap-vm1-eth0  tag=200  (enlace B → remoto a S2)
  ├─ tap-vm1-eth1  tag=0    (enlace A → local)
  ├─ tap-vm4-eth0  tag=0    (enlace A → local)
  ├─ tap-vm4-eth1  tag=100  (enlace D → remoto a S3)
  ├─ tap-vm4-eth2  tag=400  (enlace E → remoto a S2)
  └─ patch-to-wk   → br-wk (tag=150)
br-wk:
  ├─ ens4 (trunk)
  └─ patch-to-sl   tag=150 → br-sl-{slice_id}
```

**Server 2 (VM2, VM5):**
```
br-sl-{slice_id}:
  ├─ tap-vm2-eth0  tag=200  (enlace B → remoto a S1)
  ├─ tap-vm2-eth1  tag=300  (enlace C → remoto a S3)
  ├─ tap-vm5-eth0  tag=400  (enlace E → remoto a S1)
  ├─ tap-vm5-eth1  tag=500  (enlace F → remoto a S3)
  └─ patch-to-wk   → br-wk (tag=150)
br-wk:
  ├─ ens4 (trunk)
  └─ patch-to-sl   tag=150 → br-sl-{slice_id}
```

**Server 3 (VM3, VM6):**
```
br-sl-{slice_id}:
  ├─ tap-vm3-eth0  tag=100  (enlace D → remoto a S1)
  ├─ tap-vm3-eth1  tag=300  (enlace C → remoto a S2)
  ├─ tap-vm6-eth0  tag=500  (enlace F → remoto a S2)
  └─ patch-to-wk   → br-wk (tag=150)
br-wk:
  ├─ ens4 (trunk)
  └─ patch-to-sl   tag=150 → br-sl-{slice_id}
```

---

## 4. Configuración de cada tipo de Bridge

### Br-WK (`br-wk`) — Uno por Worker, creado una sola vez
- **Puerto trunk:** `ens4` (sin tag, pasa todas las VLANs).
- **Puertos de patch:** Uno por cada Slice activo en el Worker, etiquetado con `tag={vlan_slice}`.
- **Función:** Multiplexar/desmultiplexar tráfico de múltiples Slices sobre el backbone físico.
- **Persistencia:** Este bridge es **permanente**. Se crea al inicializar el Worker y NO se borra al destruir slices.

### Br-Slice (`br-sl-{slice_id}`) — Uno por Slice por Worker
- **Puertos TAP:** Un TAP por interfaz de VM, cada uno con `tag={vlan_inner}` de su enlace.
- **Puerto de patch:** Hacia el Br-WK, etiquetado con `tag={vlan_slice}` (solo si el Slice tiene enlaces remotos).
- **Función:** Aislar la topología interna del usuario. Las Vlan-Inner son locales a este bridge.
- **Limpieza:** Se destruye cuando el Slice se elimina y no queda ninguna VM de ese Slice en el Worker.

---

## 5. Resumen de Responsabilidades por Módulo

| Módulo | Responsabilidad en este modelo |
|:---|:---|
| **Networking** | Asigna la `Vlan-Slice` del pool global. Calcula las `Vlan-Inner` por enlace. Clasifica enlaces como local/remoto tras recibir el mapa de placement. Genera el `bridge_name` (`br-sl-{slice_id}`). **Adicionalmente:** pre-calcula comandos OVS para el Driver (`/ovs/commands/`), genera reglas OpenFlow de seguridad (`/security/flows/`), y genera comandos NAT/iptables para redes con salida a Internet (`/nat/commands/`). |
| **Driver** | Crea los bridges OvS (`br-sl-*`, `br-wk` si no existe). Crea TAPs, patch-ports y aplica tags. Puede consumir comandos pre-calculados del Networking (modo asistido). Aplica reglas OpenFlow con `ovs-ofctl` y comandos NAT con `iptables`. **No decide** las VLANs ni los bridges; ejecuta lo que el Networking planificó. |
| **Slice Manager** | Orquesta: solicita al Networking el plan de red DESPUÉS del placement, para que la clasificación local/remoto sea correcta. |