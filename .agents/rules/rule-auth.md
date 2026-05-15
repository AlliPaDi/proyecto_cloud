---
trigger: model_decision
description: Actívate al trabajar en el directorio /auth/, diseñar la lógica de tokens JWT, hashing de contraseñas o validación de la jerarquía STUDENT/SLICE_ADMIN/SYSTEM_ADMIN. Se requiere acceso a la tabla users de PostgreSQL
---

# Especificación Técnica: Módulo Auth

## Stack Tecnológico
- **Lenguaje:** Python 3.12
- **Framework:** FastAPI
- **ORM:** SQLAlchemy con Driver `asyncpg` (PostgreSQL)
- **Seguridad:** Passlib (Bcrypt) y PyJWT

## Responsabilidad Operativa
Gestión centralizada de identidad y control de acceso. Es el único módulo que escribe directamente en la tabla `users`.

## Endpoints Críticos
- `POST /auth/login`: Valida credenciales y retorna un JWT con los claims: `sub` (user_id), `username`, `role` y `exp`.
- `POST /auth/register`: Permite el registro de estudiantes. Si el creador es un `SLICE_ADMIN`, puede vincular automáticamente al estudiante mediante el campo `admin_id`.
- `GET /auth/verify`: Valida la firma del token y retorna el objeto de usuario y rol para consumo interno.

## Lógica de Roles (RBAC)
- **Validación de Jerarquía:** Las funciones de autorización deben verificar que un `STUDENT` tenga un `admin_id` válido apuntando a un `SLICE_ADMIN` activo antes de permitir solicitudes de Slices.
- **Cifrado:** Todas las contraseñas deben procesarse con 12 rondas de Bcrypt antes de persistirse en la base de datos.