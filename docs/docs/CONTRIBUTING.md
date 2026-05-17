# Guía de Contribución — Orquestador Cloud G1

## Estructura del Proyecto

```
Orquestador Cloud - G1/
├── .agents/rules/          ← Reglas de comportamiento por módulo (NO editar sin consenso)
├── db/
│   ├── init_schema.sql     ← DDL + datos semilla (fuente de verdad)
│   └── seeds/
│       └── full_pipeline_seed.sql  ← Data de prueba completa
├── docs/
│   ├── context/            ← Arquitectura y estándares técnicos
│   └── modules/            ← Contratos de API por módulo (inputs/outputs)
├── auth/                   ← Módulo Auth (puerto 8081)
├── image-manager/          ← Módulo Image Manager (puerto 8083)
├── slice-manager/          ← Módulo Slice Manager (puerto 8082)
├── networking/             ← Módulo Networking (puerto 8085)
├── monitoring/             ← Módulo Monitoring (puerto 8084)
├── vm-placement/           ← Módulo VM Placement (puerto 8086)
├── dispatcher/             ← Módulo Dispatcher (puerto 8087)
├── driver/                 ← Módulo Driver (puerto 8088)
├── api-gateway/            ← Módulo API Gateway (puerto 8080)
├── docker-compose.yml      ← Orquestación de todos los servicios
├── .env.example            ← Variables de entorno de referencia
└── .gitignore
```

---

## Reglas de Desarrollo

### 1. Aislamiento de entorno virtual
Cada módulo es un **proyecto Python independiente**. Crea el `.venv` **dentro** de la carpeta del módulo:

```bash
cd auth/
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

**NUNCA** instales dependencias en la raíz del monorepo.

### 2. Levantar la BD local
```bash
# Desde la raíz del proyecto
docker-compose up -d postgres

# Verificar que la BD tiene las tablas
docker exec -it orchestrator-db psql -U orchestrator -d orchestrator_db -c "\dt"

# Cargar datos de prueba (opcional)
docker exec -i orchestrator-db psql -U orchestrator -d orchestrator_db < db/seeds/full_pipeline_seed.sql
```

### 3. Levantar tu módulo en desarrollo
```bash
cd auth/
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8081
```

### 4. Agregar tu servicio al docker-compose.yml
Cuando tu módulo esté listo para integración, agrega un bloque al `docker-compose.yml` raíz:
```yaml
  auth:
    build: ./auth
    ports:
      - "8081:8081"
    env_file: .env
    depends_on:
      - postgres
```

### 5. Convenciones de Git

**Branches:**
```
feature/auth-login
feature/networking-vlan-allocation
fix/driver-rollback-cleanup
```

**Commits:**
```
[auth] feat: implement JWT login endpoint
[networking] fix: vlan_inner assignment for local links
[db] chore: add cascade delete to vm_interfaces
```

**Pull Requests:** Siempre contra `main`. Incluir:
- Qué módulo se modifica
- Endpoints nuevos/cambiados
- Si modificaste el `docker-compose.yml`

---

## Archivos de Referencia (LEER ANTES DE CODEAR)

| Archivo | Cuándo leerlo |
|:---|:---|
| `docs/context/05_Logica_Consistencia_L2.md` | Si trabajas en Networking o Driver |
| `docs/modules/{tu_modulo}_contract.md` | Siempre. Define tus inputs/outputs |
| `docs/modules/payload_schema.md` | Si escribes o lees `tasks.payload` |
| `db/init_schema.sql` | Siempre. Es el contrato universal de datos |
| `.agents/rules/rule-{tu_modulo}.md` | Siempre. Define restricciones de tu módulo |

---

## Variables de Entorno

Copia `.env.example` a `.env` y ajusta si es necesario:

```bash
cp .env.example .env
```

| Variable | Default | Módulos que la usan |
|:---|:---|:---|
| `DATABASE_URL` | `postgresql+asyncpg://orchestrator:orchestrator@localhost:5432/orchestrator_db` | Todos excepto API Gateway |
| `JWT_SECRET` | `dev-secret-key` | Auth, API Gateway |
| `JWT_ALGORITHM` | `HS256` | Auth, API Gateway |
| `SSH_ENABLED` | `false` | Monitoring, Driver |
| `IMAGE_BASE_PATH` | `/mnt/storage/base/` | Image Manager |

---

## Testing Individual de un Módulo

1. Levanta PostgreSQL: `docker-compose up -d postgres`
2. Carga el seed de tu módulo (ver `docs/modules/{modulo}_contract.md` → sección "Seed SQL")
3. Levanta tu módulo con `uvicorn`
4. Ejecuta los cURL de prueba del contrato
5. Verifica el estado en la BD:
```bash
docker exec -it orchestrator-db psql -U orchestrator -d orchestrator_db
\x on
SELECT * FROM tasks;
```
