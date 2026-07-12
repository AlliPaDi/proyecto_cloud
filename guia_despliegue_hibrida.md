# Guía de Despliegue Híbrida (Linux + OpenStack) con Gestión de Flavors

Esta guía detalla cómo probar el orquestador en ambos entornos (Linux y OpenStack) utilizando el rol **SLICE_ADMIN**. Incluye la creación de *Flavors* mediante la nueva API y el despliegue de la topología Ex1.

---

## FASE 1 — Prerrequisitos y Arranque

Asegúrate de haber levantado todos los servicios con `docker-compose`:

```bash
docker compose up -d --build
```

Y verifica que las bases de datos estén sembradas correctamente para los workers de Linux, al igual que en la guía base.

---

## FASE 2 — Autenticación

Dado que vamos a probar como **SLICE_ADMIN**, obtendremos primero el token del profesor (Slice Admin) y de paso el del alumno para pruebas si fuese necesario:

```bash
# Registrar Usuarios (si no existen)
curl -s -X POST http://localhost:8081/auth/register -H "Content-Type: application/json" -d '{"username":"profesor1","password":"Prof2026!","role":"SLICE_ADMIN"}'
curl -s -X POST http://localhost:8081/auth/register -H "Content-Type: application/json" -d '{"username":"alumno1","password":"Test2026!","role":"STUDENT","admin_id":1}'

# Token SLICE_ADMIN
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"profesor1","password":"Prof2026!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Token STUDENT
STUDENT_TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"alumno1","password":"Test2026!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

---

## FASE 3 — Registro de Flavors para el Clúster Linux

En Linux, los *Flavors* son gestionados localmente por la base de datos de Slice Manager. Para OpenStack, el orquestador los consulta dinámicamente a la API de Nova (proxy).

Vamos a crear 2 flavors básicos en Linux usando el token del Administrador:

```bash
# Flavor "tiny" (Solo Alumnos)
curl -s -X POST http://localhost:8080/api/v1/flavors/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "tiny",
    "ram": 512,
    "vcpu": 1,
    "disk": 10,
    "allowed_role": "STUDENT"
  }'

# Flavor "large" (Exclusivo para Admins)
curl -s -X POST http://localhost:8080/api/v1/flavors/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "large",
    "ram": 2048,
    "vcpu": 2,
    "disk": 20,
    "allowed_role": "SLICE_ADMIN"
  }'
```

Puedes ver la lista de *flavors* disponibles (los alumnos solo verán "tiny", los admins verán todos):
```bash
curl -s -X GET http://localhost:8080/api/v1/flavors/ \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

*Nota para OpenStack: Se asume que en el clúster remoto ya existen flavors (por ejemplo, con un ID de uuid o nombres como `m1.small`).*

---

## FASE 4 — Despliegue de la Topología Ex1 (Linux)

Desplegaremos la Topología Ex1 en el clúster local Linux. Usaremos el *Flavor* `1` (que corresponde a "tiny") para estas VMs:

```bash
curl -s -X POST http://localhost:8080/api/v1/slices/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "TopoEx1-Linux",
    "iaas_target": "linux",
    "vms": [
      {"name": "VM1", "base_image": "ubuntu-focal.qcow2", "flavor_id": 1},
      {"name": "VM2", "base_image": "debian12.qcow2", "flavor_id": 1},
      {"name": "VM3", "base_image": "ubuntu-focal.qcow2", "flavor_id": 1},
      {"name": "VM4", "base_image": "ubuntu-focal.qcow2", "flavor_id": 1},
      {"name": "VM5", "base_image": "ubuntu-focal.qcow2", "flavor_id": 1},
      {"name": "VM6", "base_image": "debian12.qcow2", "flavor_id": 1}
    ],
    "links": [
      {"vm_a": "VM1", "iface_a": "eth0", "vm_b": "INTERNET", "iface_b": "inet0"},
      {"vm_a": "VM6", "iface_a": "eth0", "vm_b": "INTERNET", "iface_b": "inet1"},
      {"vm_a": "VM1", "iface_a": "eth1", "vm_b": "VM2", "iface_b": "eth0"},
      {"vm_a": "VM2", "iface_a": "eth1", "vm_b": "VM3", "iface_b": "eth1"},
      {"vm_a": "VM3", "iface_a": "eth0", "vm_b": "VM4", "iface_b": "eth1"},
      {"vm_a": "VM1", "iface_a": "eth2", "vm_b": "VM4", "iface_b": "eth0"},
      {"vm_a": "VM4", "iface_a": "eth2", "vm_b": "VM5", "iface_b": "eth0"},
      {"vm_a": "VM5", "iface_a": "eth1", "vm_b": "VM6", "iface_b": "eth1"}
    ]
  }'
```
*Aprobar despliegue:*
```bash
curl -s -X POST http://localhost:8080/api/v1/slices/1/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## FASE 5 — Despliegue de la Topología Ex1 (OpenStack)

Ahora desplegaremos la **misma topología** pero delegando todo el control al clúster remoto OpenStack.
Fíjate que el `iaas_target` cambia a `"openstack"`, y pasamos el nombre o ID real del flavor en OpenStack (ej: `m1.small` o el UUID).

```bash
curl -s -X POST http://localhost:8080/api/v1/slices/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test2026",
    "iaas_target": "openstack",
    "vms": [
      {
        "name": "VM1",
        "flavor": "eb0bdaf9-4803-415c-8857-7956fefead50",
        "base_image": "a61a8583-016c-4e19-9d45-e634a627c213"
      },
      {
        "name": "VM2",
        "flavor": "eb0bdaf9-4803-415c-8857-7956fefead50",
        "base_image": "a61a8583-016c-4e19-9d45-e634a627c213"
      },
      {
        "name": "VM3",
        "flavor": "eb0bdaf9-4803-415c-8857-7956fefead50",
        "base_image": "a61a8583-016c-4e19-9d45-e634a627c213"
      },
      {
        "name": "VM4",
        "flavor": "eb0bdaf9-4803-415c-8857-7956fefead50",
        "base_image": "a61a8583-016c-4e19-9d45-e634a627c213"
      },
      {
        "name": "VM5",
        "flavor": "eb0bdaf9-4803-415c-8857-7956fefead50",
        "base_image": "a61a8583-016c-4e19-9d45-e634a627c213"
      },
      {
        "name": "VM6",
        "flavor": "eb0bdaf9-4803-415c-8857-7956fefead50",
        "base_image": "a61a8583-016c-4e19-9d45-e634a627c213"
      }
    ],
    "networks": [
      {
        "name": "net_vm6_vm5",
        "cidr": "10.100.60.0/24",
        "is_provider": false
      },
      {
        "name": "net_vm5_vm4",
        "cidr": "10.100.10.0/24",
        "is_provider": false
      },
      {
        "name": "net_vm4_vm1",
        "cidr": "10.100.1.0/24",
        "is_provider": false
      },
      {
        "name": "net_vm1_vm2",
        "cidr": "10.100.2.0/24",
        "is_provider": false
      },
      {
        "name": "net_vm2_vm3",
        "cidr": "10.100.3.0/24",
        "is_provider": false
      },
      {
        "name": "net_vm3_vm4",
        "cidr": "10.100.4.0/24",
        "is_provider": false
      },
      {
        "name": "external",
        "is_provider": true
      }
    ],
    "links": [
      {
        "vm_a": "VM6",
        "iface_a": "eth0",
        "vm_b": "VM5",
        "iface_b": "eth0"
      },
      {
        "vm_a": "VM5",
        "iface_a": "eth1",
        "vm_b": "VM4",
        "iface_b": "eth0"
      },
      {
        "vm_a": "VM4",
        "iface_a": "eth1",
        "vm_b": "VM1",
        "iface_b": "eth0"
      },
      {
        "vm_a": "VM1",
        "iface_a": "eth1",
        "vm_b": "VM2",
        "iface_b": "eth0"
      },
      {
        "vm_a": "VM2",
        "iface_a": "eth1",
        "vm_b": "VM3",
        "iface_b": "eth0"
      },
      {
        "vm_a": "VM3",
        "iface_a": "eth1",
        "vm_b": "VM4",
        "iface_b": "eth2"
      },
      {
        "vm_a": "VM5",
        "iface_a": "eth2",
        "vm_b": "external",
        "iface_b": "wan"
      },
      {
        "vm_a": "VM4",
        "iface_a": "eth3",
        "vm_b": "external",
        "iface_b": "wan"
      }
    ]
  }'
```


> **NOTA:** El orquestador consultará en tiempo real el catálogo de Nova (proxy) para obtener los valores de RAM, vCPU y Disco de `m1.small`, permitiendo registrar la máquina virtual con capacidades reales, y además alimentará al sistema de Placement para la distribución correcta entre los Hosts OpenStack.
