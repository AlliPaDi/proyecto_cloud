# Auth — Contrato de API (Puerto 8081)

## Endpoints

### POST /auth/register
**Input:**
```json
{
  "username": "alumno1",
  "password": "SecurePass123!",
  "role": "STUDENT",
  "admin_id": 1
}
```
- `role`: `STUDENT` | `SLICE_ADMIN` | `SYSTEM_ADMIN`
- `admin_id`: Obligatorio si `role=STUDENT`. ID del SLICE_ADMIN asignado.

**Output (201):**
```json
{
  "id": 5,
  "username": "alumno1",
  "role": "STUDENT",
  "admin_id": 1,
  "quota_ram": 4096,
  "quota_cpu": 4
}
```

**Errores:**
- `409`: Username ya existe.
- `400`: `admin_id` no corresponde a un SLICE_ADMIN.

---

### POST /auth/login
**Input:**
```json
{
  "username": "alumno1",
  "password": "SecurePass123!"
}
```

**Output (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Claims del JWT:**
```json
{
  "sub": 5,
  "username": "alumno1",
  "role": "STUDENT",
  "exp": 1715400000
}
```

**Errores:**
- `401`: Credenciales inválidas.

---

### GET /auth/verify
**Headers:** `Authorization: Bearer <token>`

**Output (200):**
```json
{
  "id": 5,
  "username": "alumno1",
  "role": "STUDENT",
  "admin_id": 1
}
```

**Errores:**
- `401`: Token inválido o expirado.

---

## Seed SQL para testing
```sql
-- Ejecutar DESPUÉS de init_schema.sql
-- Crea la jerarquía de roles para probar Auth

INSERT INTO users (username, password_hash, role) VALUES
  ('sysadmin', '$2b$12$HASH_PLACEHOLDER', 'SYSTEM_ADMIN');

INSERT INTO users (username, password_hash, role) VALUES
  ('profesor1', '$2b$12$HASH_PLACEHOLDER', 'SLICE_ADMIN');

-- El alumno1 se crea vía POST /auth/register para probar el endpoint
```

## Test cURL
```bash
# 1. Registrar un alumno
curl -X POST http://localhost:8081/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alumno1","password":"test1234","role":"STUDENT","admin_id":2}'

# 2. Login
curl -X POST http://localhost:8081/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alumno1","password":"test1234"}'

# 3. Verificar token (reemplazar TOKEN)
curl http://localhost:8081/auth/verify \
  -H "Authorization: Bearer TOKEN"
```
