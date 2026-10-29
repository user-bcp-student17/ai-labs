# Impacto técnico: Issue #22 (verificación JWT para H-API-04)

Spec de referencia: [openspec/changes/verify-api-jwt-signatures](../../openspec/changes/verify-api-jwt-signatures/proposal.md).

## Estado del código frente a la spec

- [api/app/security.py](../../api/app/security.py) ya acepta solo RS256, exige `sub`, `iss`, `aud` y `exp`, lee `AUTH_JWT_PUBLIC_KEY`, `AUTH_JWT_ISSUER` y `AUTH_JWT_AUDIENCE`, convierte `\\n` en saltos de línea y responde `401` o `503` con los mensajes definidos.
- [compose.yaml](../../compose.yaml) pasa las tres variables al servicio API con valores vacíos por defecto.
- [docs/ENDPOINTS.md](../ENDPOINTS.md) describe el contrato actualizado en su línea 9.

## Impactos y riesgos

1. **Rotura del flujo login a API (alto).** [auth/LegacyTokenUtil.java](../../auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java) sigue emitiendo tokens Base64 con secreto fijo. La API los rechaza con `401`. Coincide con H-AUTH-02 (#26); ambos cambios deben coordinarse antes del despliegue.
2. **Documentación contradictoria (medio).** [docs/ENDPOINTS.md](../ENDPOINTS.md) líneas 189 y 305 indican que la API acepta Base64 legacy y que H-API-04 está pendiente. Contradicen la línea 9 y el código. Corresponde a la tarea 3.2.
3. **Estado inconsistente (medio).** [HALLAZGOS.md](../../HALLAZGOS.md) marca H-API-04 como `Resuelto`, mientras todas las tareas de [tasks.md](../../openspec/changes/verify-api-jwt-signatures/tasks.md) siguen sin marcar.
4. **Configuración vacía por defecto (medio).** Sin las tres variables, todas las rutas protegidas responden `503`. El despliegue debe fijarlas.
5. **Logs sin verificar (bajo).** No se ha comprobado con pruebas que no se registren tokens ni claves (tarea 1.4).
6. **Fuera de alcance (bajo).** El bypass de `owner=` vacío (H-API-02) no cambia con esta spec.

## Pruebas

[api/tests/test_api.py](../../api/tests/test_api.py) ya cubre varios casos de caracterización. Antes de cualquier ajuste, verificar la cobertura de las tareas 1.1 a 1.4.

## Recomendación

- No cerrar H-API-04 hasta que `auth/` emita RS256 o exista una transición acordada.
- Corregir primero la documentación inconsistente y completar las pruebas de caracterización pendientes.
- Decisiones pendientes para aprobación humana: alcance de la transición con `auth/` y estado final de H-API-04.
