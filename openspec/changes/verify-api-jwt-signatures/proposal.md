# Proposal

## Why

El Issue [#22](https://github.com/user-bcp-student17/ai-labs/issues/22), “API: verify JWT signatures for H-API-04”, aborda la aceptación de tokens cuya identidad no está respaldada por una firma verificable. Verificar la identidad y rechazar el formato legacy protege los datos de las cinco rutas y mantiene la autenticación coherente con el contrato publicado.

## What Changes

- Sustituir la aceptación del token Base64 legacy por credenciales Bearer JWT firmadas con RS256 y claims `sub`, `iss`, `aud` y `exp` obligatorios y válidos.
- Obtener la clave pública, el emisor y la audiencia de configuración externa; rechazar credenciales inválidas con `401` y configuración JWT ausente o inválida con `503`, según el contrato documentado.
- Aplicar la identidad verificada a las cinco rutas de la API sin alterar sus respuestas exitosas ni el formato `Authorization: Bearer`.
- Exponer la configuración necesaria en Compose y documentar el contrato actualizado, sin registrar valores sensibles.

**Fuera de alcance:** cambios al servicio `auth/` o a su emisor; integración real entre ambos servicios; remediación de H-API-07; cambios a las reglas de `owner` de H-API-02; y cambios de validación de archivos de H-API-03.

**Comportamiento que se preserva:** las rutas `GET /api/tasks`, `POST /api/tasks`, `GET /api/summary`, `POST /api/requirements` y `GET /api/backend-health` conservan sus métodos, paths, headers Bearer, respuestas exitosas y formatos documentados en `docs/ENDPOINTS.md`. La falta de autorización o las credenciales inválidas siguen respondiendo `401` con `{"detail":"Invalid token"}`. La configuración de autenticación no disponible responde `503` con `{"detail":"Authentication configuration unavailable"}`. El Issue concreta el perfil de identidad criptográfica para H-API-04; no cambia esos contratos de endpoint.

## Capabilities

### New Capabilities
- `api-authentication`: autenticación de las rutas de la API mediante identidad JWT verificada y configuración externa.

### Modified Capabilities
- Ninguna. El repositorio no tiene specs existentes; esta capability nueva formaliza el comportamiento comprometido por el Issue #22 y ya reflejado en el baseline de `docs/ENDPOINTS.md`.

## Impact

- Componente `api/`: autenticación de las cinco rutas, pruebas de contrato y dependencias relacionadas.
- Configuración de ejecución en Compose y documentación del contrato de API.
- No se modifican código funcional, pruebas, documentación general ni componentes fuera de `api/` en esta propuesta.