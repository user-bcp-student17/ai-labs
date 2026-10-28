# Revisión de compatibilidad — PR #22

- PR: [#22 — API: verify JWT signatures for H-API-04](https://github.com/user-bcp-student17/ai-labs/pull/22)
- Repositorio: `user-bcp-student17/ai-labs`
- Base: `main` (`cb5379576a5310d4154b8978f90d73aa51e8b55d`)
- Cabeza: `fix/api-h-api-04-jwt` (`d2fb14b3be80b44f80e7dd7126297d73150098d6`)
- Aspecto: compatibilidad
- Criterio: preservar métodos/rutas y formatos de request/response, códigos HTTP y contratos de autenticación para consumidores existentes; diferenciar ruptura demostrada de migración que requiere confirmación.

## Observaciones

### Riesgo que requiere confirmación — clientes que aún emiten tokens legacy perderán acceso

- **Evidencia del diff:** en `api/app/routes.py`, los hunks de las cinco rutas cambian la dependencia `Depends(legacy_identity)` a `Depends(verified_identity)` (por ejemplo, hunk `@@ -43,7 +43,7 @@ def list_tasks`). En `api/app/security.py`, hunk `@@ -1,23 +1,60 @@`, la función nueva llama a `jwt.decode` con `algorithms=[JWT_ALGORITHM]` y exige `JWT_REQUIRED_CLAIMS`; el diff elimina `legacy_identity`. El diff de `api/tests/test_api.py` añade `test_rejects_legacy_base64_token` (línea 363 en la cabeza), que espera HTTP 401 para un token legacy.
- **Impacto:** consumidores que todavía usen el formato Base64 previo recibirán 401 en las rutas protegidas. La nueva exigencia de JWT RS256 con `sub`, `iss`, `aud` y `exp` muestra que la incompatibilidad de formato es intencional en este PR; no demuestra que todos los emisores/consumidores se hayan migrado. El PR declara que no se ejecutó integración con Auth.
- **Clasificación:** no es un defecto demostrado con la evidencia disponible; es un riesgo de despliegue/interoperabilidad hasta comprobar el emisor real y consumidores.
- **Confirmación:** verificar que el servicio emisor de Auth genere JWT RS256 con los claims exigidos y que cada consumidor envíe ese token en `Authorization: Bearer`. Ejecutar una prueba integrada Auth→API y una prueba de contrato de las rutas protegidas; confirmar que ningún consumidor soportado depende del formato legacy.

### Riesgo que requiere confirmación — configuración JWT ausente produce HTTP 503

- **Evidencia del diff:** en `api/app/security.py`, el hunk `@@ -1,23 +1,60 @@` añade una rama que lanza `HTTPException(status_code=503, detail=AUTHENTICATION_UNAVAILABLE_DETAIL)` cuando `_jwt_configuration()` no encuentra la clave pública, issuer o audience. El test añadido `test_missing_jwt_configuration_fails_closed` (línea 374 en la cabeza) confirma por aserción que el resultado esperado es `503` con `{"detail":"Authentication configuration unavailable"}`. El cuerpo del PR especifica que esas variables de entorno deben configurarse.
- **Impacto:** un despliegue sin las tres variables no podrá autenticar las peticiones protegidas; las solicitudes con configuración ausente ya no presentan la misma respuesta que un token inválido (`401`). El PR documenta la configuración externa y expone esas variables en Compose, pero no demuestra aquí que todos los entornos consumidores estén configurados o que sus clientes manejen `503`.
- **Clasificación:** riesgo de integración/configuración, no defecto demostrado.
- **Confirmación:** comprobar la configuración efectiva en cada entorno de despliegue y hacer una prueba de humo que verifique una respuesta exitosa con configuración válida, además del `503` documentado cuando falta. Revisar que los clientes distingan indisponibilidad de configuración de credenciales inválidas.

## Comprobaciones realizadas

- Consulté mediante GitHub MCP los detalles y el diff del PR #22. Los SHAs registrados corresponden a `base.sha` y `head.sha` reportados por MCP.
- Comparé el `api/app/routes.py` y `api/app/security.py` de la base y de la cabeza, y consulté el contrato existente en `docs/ENDPOINTS.md` a SHA base. El contrato de rutas y respuestas exitosas no muestra cambios en las líneas de endpoints; los cambios visibles en `routes.py` sustituyen el mecanismo de identidad. Las pruebas nuevas de la cabeza incluyen respuestas exitosas `200`/`201`, rechazo de token legacy `401` y falta de configuración `503`.
- El alcance fue solo compatibilidad; no hice una auditoría de seguridad ni una revisión general de calidad.
- Inspeccioné el código y los tests del diff mediante MCP; **no ejecuté pruebas**. El resultado `46 passed, 2 xfailed` y la cobertura que aparecen en la descripción son reportados por el PR, no validados en esta revisión.
- No comprobé el emisor Auth real ni clientes externos/de despliegue, por lo que ambos riesgos requieren las confirmaciones indicadas.

La revisión es local. No se publicó comentario, review ni aprobación del PR; este análisis no constituye aprobación.
