---
trigger: model_decision
description: Actívate en /api-gateway/ al definir rutas de proxy, middleware de seguridad o propagación del header X-User-Role. Gestiona el tráfico hacia los servicios de auth, slice-manager y monitoring
---

# Especificación Técnica: API Gateway

## Stack Tecnológico
- **Lenguaje:** Python 3.12
- **Framework:** FastAPI
- **Cliente HTTP:** `httpx` (Asíncrono para Forwarding)
- **Token Handling:** PyJWT (Solo lectura)

## Responsabilidad Operativa
Actuar como Proxy Reverso y terminador de autenticación. Centraliza la validación de seguridad antes de que la petición toque los módulos internos.

## Middleware de Seguridad
1. **Auth Extractor:** Debe interceptar el header `Authorization: Bearer <token>`, decodificarlo y validar su vigencia.
2. **Role Injection:** Tras la validación, debe inyectar el header `X-User-Role` en la petición que se reenvía al microservicio destino.
3. **CORS:** Configurado estrictamente para el dominio del dashboard del proyecto.

## Mapeo de Rutas (Proxy Logic)
- `/api/v1/auth/*` -> Reenvío a `auth:8081`
- `/api/v1/slices/*` -> Reenvío a `slice-manager:8082`
- `/api/v1/infra/*` -> Reenvío a `monitoring:8084` (Restringido a `SYSTEM_ADMIN`).

## Restricciones Técnicas
- **Stateless:** El Gateway no debe guardar estado ni sesiones locales.
- **Payload Limit:** Restringir el tamaño de los JSON de topología a 2MB para evitar ataques de denegación de servicio en el parsing inicial.