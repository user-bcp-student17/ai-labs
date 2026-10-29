# Spec Delta

## Purpose

Define el contrato de autenticación de la API para que sus rutas protegidas usen una identidad respaldada por un JWT verificable y configuración externa.

## ADDED Requirements

### Requirement: Authenticate requests with a verified JWT identity
Las rutas protegidas MUST aceptar credenciales Bearer solo si el JWT tiene firma RS256 verificable, incluye `sub`, `iss`, `aud` y `exp`, y sus valores de emisor, audiencia y expiración son válidos. La identidad usada por la API MUST derivarse de `sub`; `role` es opcional y no concede autorización.

#### Scenario: Valid JWT authenticates as its subject
- **WHEN** una solicitud a una ruta protegida presenta un Bearer JWT con firma, claims requeridos y valores válidos
- **THEN** la API procesa la solicitud usando el valor `sub` como identidad autenticada

#### Scenario: Role claim is absent
- **WHEN** una solicitud presenta un JWT válido sin claim `role`
- **THEN** la autenticación puede completarse y la ruta no concede permisos basándose en `role`

### Requirement: Reject invalid and legacy credentials
Las rutas protegidas MUST rechazar con `401` las credenciales ausentes, malformadas, vencidas, con claims requeridos ausentes o inválidos, con firma no verificable, o que no sean un JWT aceptado. La respuesta MUST ser `{"detail":"Invalid token"}`.

#### Scenario: JWT signature or claims are invalid
- **WHEN** una solicitud presenta un token vencido, con emisor o audiencia incorrectos, claims requeridos ausentes o una firma inválida
- **THEN** la API responde `401` con `{"detail":"Invalid token"}` y no procesa la operación

#### Scenario: Legacy Base64 credential is presented
- **WHEN** una solicitud presenta el formato de token Base64 legacy como credencial Bearer
- **THEN** la API responde `401` con `{"detail":"Invalid token"}`

#### Scenario: Authorization is missing or malformed
- **WHEN** una solicitud a una ruta protegida no incluye una credencial Bearer válida
- **THEN** la API responde `401` con `{"detail":"Invalid token"}`

### Requirement: Load JWT verification settings from external configuration
La API MUST obtener la clave pública, el emisor y la audiencia de `AUTH_JWT_PUBLIC_KEY`, `AUTH_JWT_ISSUER` y `AUTH_JWT_AUDIENCE`, sin requerir esos valores en la solicitud del cliente.

#### Scenario: JWT verification configuration is unavailable
- **WHEN** la credencial Bearer está presente pero falta o no es válida la configuración JWT
- **THEN** la API responde `503` con `{"detail":"Authentication configuration unavailable"}` y no procesa la operación

#### Scenario: PEM public key uses escaped newlines
- **WHEN** la clave pública configurada representa sus saltos de línea como `\\n`
- **THEN** la API puede usarla para verificar un JWT firmado correctamente

### Requirement: Make JWT settings available to deployments and documentation
El despliegue de la API MUST permitir suministrar externamente las tres variables de verificación, y la documentación MUST identificar sus nombres y describir la respuesta ante configuración no disponible sin incluir valores sensibles.

#### Scenario: Deployment can provide JWT settings without repository secrets
- **WHEN** el despliegue de la API se configura con valores aislados para la clave pública, el emisor y la audiencia
- **THEN** la API recibe esos valores para verificar tokens y la documentación identifica las tres variables y el error `503` correspondiente sin incluir credenciales reales

### Requirement: Preserve the documented contract of protected API routes
La autenticación MUST proteger `GET /api/tasks`, `POST /api/tasks`, `GET /api/summary`, `POST /api/requirements` y `GET /api/backend-health` sin cambiar sus métodos, paths ni respuestas exitosas documentadas en `docs/ENDPOINTS.md`.

#### Scenario: Valid identity reaches each protected route
- **WHEN** una solicitud autenticada válida usa el método y path documentados para cualquiera de las cinco rutas protegidas
- **THEN** la ruta conserva el status exitoso, los campos de respuesta y el comportamiento descritos para esa operación en `docs/ENDPOINTS.md`

#### Scenario: Invalid credentials are rejected consistently across routes
- **WHEN** cualquiera de las cinco rutas recibe credenciales ausentes o inválidas
- **THEN** responde `401` con `{"detail":"Invalid token"}` sin ejecutar la operación

### Requirement: Do not expose authentication material in logs
La API MUST NOT registrar tokens, credenciales ni valores de material de clave durante la autenticación, incluso cuando una credencial o la configuración sea inválida.

#### Scenario: Authentication fails without logging credential values
- **WHEN** la verificación de una credencial falla o la configuración de autenticación no está disponible
- **THEN** los registros no contienen el token, la credencial ni el material de clave involucrado