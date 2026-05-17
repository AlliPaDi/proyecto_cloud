# 04. Estándares Técnicos: Virtualización y Red

## 1. Reglas de QEMU y Almacenamiento (Server 4)
- **Ruta de Imágenes:** `/mnt/storage/base/` para imágenes de SO y `/mnt/storage/instances/` para discos de VMs creadas.
- **Comando Obligatorio:** `qemu-img create -f qcow2 -b {base_path} {inst_path}`.
- **Captura de PID:** Uso mandatorio de `-pidfile /tmp/{vm_name}.pid` para auditoría inmediata.

## 2. Networking y Aislamiento L2
- **Data Network (ens4):** Configurada como puerto Trunk en el `Br-WK` (bridge de transporte por Worker).
- **Modelo de Aislamiento:** Jerarquía de 3 capas: `Br-Slice` (topología interna) + `Vlan-Inner` (enlaces lógicos) + `Vlan-Slice` (transporte inter-worker). Ver `05_Logica_Consistencia_L2.md`.
- **Gestión (ens3):** Prohibido realizar configuraciones de red sobre esta interfaz para no perder el acceso SSH.

## 3. Seguridad Intra-Slice (OpenFlow)
- El tráfico VM↔VM dentro del Br-Slice se controla con reglas OpenFlow (`ovs-ofctl`), no con `iptables`.
- Política por defecto: ARP permitido, todo IP denegado. Las reglas del usuario se definen en la tabla `security_rules`.

## 4. NAT / Salida a Internet
- Redes con `internet_access=TRUE` habilitan salida a Internet vía `iptables MASQUERADE` por `ens4`.
- El tráfico VM→Internet SÍ pasa por el kernel del Worker (a diferencia del tráfico intra-Br-Slice que OvS maneja sin kernel).