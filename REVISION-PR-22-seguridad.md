# Revisión de seguridad — PR #22

- PR: [#22 — API: verify JWT signatures for H-API-04](https://github.com/user-bcp-student17/ai-labs/pull/22)
- Repositorio: `user-bcp-student17/ai-labs`
- Base: `main` (`cb5379576a5310d4154b8978f90d73aa51e8b55d`)
- Cabeza: `fix/api-h-api-04-jwt` (`d2fb14b3be80b44f80e7dd7126297d73150098d6`)
- Alcance: verificación JWT, integración de las rutas API, configuración Compose y flujo de emisión de tokens pertinente.

## Hallazgo

### Riesgo que requiere confirmación — posible incompatibilidad entre el login incluido y el validador JWT de la API

- **Severidad:** Baja
- **Confianza:** 9/10
- **Ubicación del cambio:** `api/app/routes.py:34`; `api/app/security.py:38-45`; configuración JWT modificada en `compose.yaml:11-13`.
- **Evidencia:** el diff de `api/app/routes.py` cambia la dependencia de autenticación de la ruta a `verified_identity`. En `api/app/security.py`, esa función verifica JWT con algoritmo RS256 y exige `sub`, `iss`, `aud` y `exp`. El flujo de login incluido, inspeccionado en la cabeza exacta, sigue usando `LegacyTokenUtil` para emitir un token codificado en Base64 legacy, no un JWT RS256. La configuración JWT de Compose tiene valores predeterminados vacíos.
- **Impacto y condición:** si el login incluido sigue siendo el emisor previsto para los consumidores de esta API, sus tokens no satisfarán el nuevo validador; con la configuración requerida vacía, la API responde `503`. No se demuestra una evasión de autorización ni exposición de datos. El PR indica que no se ejecutó integración con Auth, por lo que la intención de despliegue y el emisor de producción siguen pendientes de confirmar.
- **Confirmación defensiva:** ejecutar una prueba de integración de login → ruta API protegida en la configuración Compose/despliegue prevista. Verificar que el emisor configurado entregue un token RS256 aceptado y que clave pública, issuer y audience correspondan a ese emisor.

## Comprobaciones y límites

- Se consultaron mediante GitHub MCP los metadatos y el diff del PR, y archivos pertinentes fijados a los SHA exactos de base y cabeza.
- Se revisaron verificación JWT, las comprobaciones de propietario de rutas API, las rutas de carga y health, la configuración JWT de Compose, y la generación de token del login incluido.
- Se inspeccionaron los tests relativos a firmas/claims inválidos, configuración ausente, rechazo de token legacy y rutas protegidas. **No se ejecutaron pruebas ni herramientas locales** en esta revisión.
- El agente de revisión reportó que la metadata de checks de GitHub mostraba API y Auth exitosos; Dependency Review falló porque no era compatible con el repositorio y CodeQL tuvo estado neutral. El resultado de `pip-audit` está descrito por el PR y no fue verificado independientemente en esta revisión.
- No se demostró una vulnerabilidad confirmada de acceso no autorizado o exposición de datos. El único hallazgo es el riesgo de interoperabilidad de autenticación descrito arriba.

La revisión es local; no se publicó comentario, review ni aprobación del PR. No constituye aprobación del PR.
