# API Gateway — Contrato de API (Puerto 8080)

## Mapeo de Rutas

| Ruta externa | Servicio destino | Restricción de rol |
|:---|:---|:---|
| `/api/v1/auth/*` | `auth:8081` | Ninguna (público) |
| `/api/v1/slices/*` | `slice-manager:8082` | STUDENT, SLICE_ADMIN, SYSTEM_ADMIN |
| `/api/v1/images/*` | `image-manager:8083` | STUDENT, SLICE_ADMIN, SYSTEM_ADMIN |
| `/api/v1/infra/*` | `monitoring:8084` | Solo SYSTEM_ADMIN |
| `/api/v1/networking/*` | `networking:8085` | Solo SYSTEM_ADMIN (interno) |
| `/api/v1/placement/*` | `vm-placement:8086` | Solo SYSTEM_ADMIN (debug) |

## Comportamiento del Middleware

### 1. Flujo de autenticación
```
Request → ¿Tiene header Authorization? 
  → NO: ¿Ruta es /api/v1/auth/*? → SÍ: Pasar sin token → NO: 401
  → SÍ: Decodificar JWT → Extraer role → Inyectar X-User-Id y X-User-Role → Proxy al servicio
```

### 2. Headers inyectados
```
X-User-Id: 5         ← claim "sub" del JWT
X-User-Role: STUDENT  ← claim "role" del JWT
```

### 3. CORS
```
Access-Control-Allow-Origin: *  (en desarrollo)
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

---

## Endpoints del propio Gateway

### GET /health
```json
{"status": "ok", "services": {"auth": "up", "slice-manager": "up", "monitoring": "up"}}
```

---

## Ejemplo completo (flujo end-to-end)

```bash
# 1. Login (sin token, ruta pública)
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alumno1","password":"test1234"}'
# Respuesta: {"access_token": "eyJ..."}

# 2. Crear Slice (con token)
curl -X POST http://localhost:8080/api/v1/slices/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "name": "Mi-Topo",
    "vms": [{"name":"VM1","base_image":"ubuntu-22.04.qcow2","ram":512,"vcpu":1}],
    "links": []
  }'
# El Gateway decodifica el token, inyecta X-User-Id: 5, X-User-Role: STUDENT
# y reenvía a slice-manager:8082

# 3. Ver Workers (requiere SYSTEM_ADMIN, sino → 403)
curl http://localhost:8080/api/v1/infra/workers \
  -H "Authorization: Bearer eyJ_SYSADMIN_TOKEN..."
```

## Seed SQL para testing
```sql
-- El Gateway NO accede a la BD directamente.
-- Para testear, se necesitan los servicios Auth y Slice Manager corriendo.
-- Seed mínimo: un usuario para hacer login.

INSERT INTO users (username, password_hash, role) VALUES
  ('sysadmin', '$2b$12$placeholder', 'SYSTEM_ADMIN');
INSERT INTO users (username, password_hash, role) VALUES
  ('profesor1', '$2b$12$placeholder', 'SLICE_ADMIN');
INSERT INTO users (username, password_hash, role, admin_id) VALUES
  ('alumno1', '$2b$12$placeholder', 'STUDENT', 2);
```

## Configuración
```bash
AUTH_URL=http://auth:8081
SLICE_MANAGER_URL=http://slice-manager:8082
IMAGE_MANAGER_URL=http://image-manager:8083
MONITORING_URL=http://monitoring:8084
JWT_SECRET=dev-secret-key
```
