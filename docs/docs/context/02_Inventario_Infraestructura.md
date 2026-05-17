# 02. Inventario de Infraestructura: Entorno VNRT

## 1. Mapa de Nodos (Virtual Network Research Testbed)
El orquestador opera sobre un slice de infraestructura pre-aprovisionado. El acceso se realiza mediante una VPN de grupo.

| Hostname | IP Management (ens3) | Puerto SSH (Forwarding) | Rol en el Proyecto |
| :--- | :--- | :--- | :--- |
| **gateway** | 10.0.10.100 | - | Salida a Internet / NAT |
| **server 1** | 10.0.10.1 | 5801 | Worker 1 (Cómputo) |
| **server 2** | 10.0.10.2 | 5802 | Worker 2 (Cómputo) |
| **server 3** | 10.0.10.3 | 5803 | Worker 3 (Cómputo) |
| **server 4** | 10.0.10.4 | 5804 | HeadNode (Control Plane) |
| **OFS** | 10.0.10.5 | 5811 | OpenFlow Switch (L2 Fabric) |

## 2. Segmentación de Redes (Planos)

### A. Red de Management (Control Plane)
* **Interfaz:** `ens3` en todos los servidores.
* **Subred:** `10.0.10.0/24`.
* **Función:** Tráfico SSH, comunicación entre microservicios y acceso a bases de datos.
* **⚠️ REGLA DE ORO:** Está terminantemente prohibido modificar la configuración de `ens3` o agregar puentes OvS sobre esta interfaz.

### B. Red de Datos (Data Plane)
* **Interfaz:** `ens4` en todos los servidores.
* **Conectividad:** Conectada físicamente al **OFS** central.
* **Función:** Tráfico de las máquinas virtuales (VMs) de los usuarios.
* **Configuración:** Se deben crear puentes **Open vSwitch (br-int)** que utilicen `ens4` como puerto Trunk para transportar las VLANs de los slices.

## 3. Acceso y Credenciales
* **Usuario:** `ubuntu`
* **Password:** `ubuntu`
* **Modelo de Acceso:** El Nodo de Control (Server 4) debe tener configuradas llaves SSH (RSA/ED25519) para acceder sin contraseña a los Workers (Servers 1, 2 y 3).

## 4. Clasificación de Recursos (Access Control)

### Recursos Gestionados (Managed):
* **Workers (S1, S2, S3):** El agente puede ejecutar comandos de red (`ovs-vsctl`) y virtualización (`qemu`).
* **HeadNode (S4):** El agente puede desplegar contenedores, gestionar el NAT para las VMs y administrar las BDs.

### Recursos de Soporte (Fabric - Read Only):
* **Gateway & OFS:** Se consideran "Caja Negra". El agente NO debe intentar conectarse por SSH ni alterar su configuración. Su única función es proveer conectividad L2 (OFS) y salida L1 (Gateway).

## 5. Especificaciones de Hardware (Referencia)
* **Modelo:** DELL Power Edge R630.
* **Almacenamiento:** Las imágenes base residen en `/mnt/storage/base/` y los discos de instancia en `/mnt/storage/instances/` (Shared Storage en Server 4, montado vía NFS en los Workers).