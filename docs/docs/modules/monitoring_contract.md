# Monitoring — Contrato de API (Puerto 8084)

## Endpoints

### GET /monitoring/workers
Lista el estado actual de todos los Workers.

**Headers:** `X-User-Role: SYSTEM_ADMIN`

**Output (200):**
```json
{
  "workers": [
    {
      "id": 1,
      "hostname": "server1",
      "ip_management": "10.0.10.1",
      "total_ram": 8192,
      "total_cpu": 4,
      "current_cpu_load": 35.20,
      "current_ram_available": 4096,
      "status": "ALIVE",
      "updated_at": "2026-05-12T10:00:00"
    },
    {
      "id": 2,
      "hostname": "server2",
      "ip_management": "10.0.10.2",
      "total_ram": 8192,
      "total_cpu": 4,
      "current_cpu_load": 12.50,
      "current_ram_available": 6144,
      "status": "ALIVE",
      "updated_at": "2026-05-12T10:00:00"
    },
    {
      "id": 3,
      "hostname": "server3",
      "ip_management": "10.0.10.3",
      "total_ram": 0,
      "total_cpu": 0,
      "current_cpu_load": 0.0,
      "current_ram_available": 0,
      "status": "DOWN",
      "updated_at": "2026-05-12T09:55:00"
    }
  ]
}
```

---

### GET /monitoring/workers/{id}
Detalle de un Worker específico.

**Output (200):** Un objeto Worker individual (mismo formato que arriba).

**Errores:**
- `404`: Worker no encontrado.

---

### GET /health
Health check del servicio.

**Output (200):**
```json
{
  "status": "ok",
  "ssh_enabled": true,
  "last_poll": "2026-05-12T10:00:00"
}
```

---

## Visibilidad por Roles
| Rol | Alcance |
|:---|:---|
| SYSTEM_ADMIN | Todos los Workers + todas las VMs |
| SLICE_ADMIN | Workers que hospedan VMs de sus alumnos |
| STUDENT | Solo métricas de sus propias VMs |

## Seed SQL para testing
```sql
-- Simular Workers con métricas ya descubiertas (sin necesidad de SSH real)
UPDATE workers SET total_ram = 8192, total_cpu = 4,
  current_cpu_load = 35.20, current_ram_available = 4096,
  status = 'ALIVE' WHERE id = 1;

UPDATE workers SET total_ram = 8192, total_cpu = 4,
  current_cpu_load = 12.50, current_ram_available = 6144,
  status = 'ALIVE' WHERE id = 2;

UPDATE workers SET total_ram = 8192, total_cpu = 4,
  current_cpu_load = 0.0, current_ram_available = 0,
  status = 'DOWN' WHERE id = 3;
```

## Test cURL
```bash
# Listar todos los Workers (como SYSTEM_ADMIN)
curl http://localhost:8084/monitoring/workers \
  -H "X-User-Role: SYSTEM_ADMIN"

# Detalle de Worker 1
curl http://localhost:8084/monitoring/workers/1 \
  -H "X-User-Role: SYSTEM_ADMIN"

# Health check
curl http://localhost:8084/health
```

## Configuración local
```bash
# Desactivar SSH para pruebas sin servidores reales
SSH_ENABLED=false
```
