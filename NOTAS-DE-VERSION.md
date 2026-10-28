# Notas de versión

Repositorio: [`user-bcp-student17/ai-labs`](https://github.com/user-bcp-student17/ai-labs)  
Intervalo: `cb5379576a5310d4154b8978f90d73aa51e8b55d` (exclusivo) → `main` en `d2fb14b3be80b44f80e7dd7126297d73150098d6` (inclusivo)

El SHA inicial corresponde al `base.sha` registrado en el PR #22 y fue resuelto mediante GitHub MCP. El SHA final corresponde a la rama `main`, también resuelta mediante GitHub MCP. Solo se incluyen integraciones demostradas dentro de `(SHA inicial, SHA final]`.

## Cambios

### La API verifica tokens JWT firmados

- **Efecto:** la API reemplaza la aceptación del formato legacy codificado en Base64 por la verificación de firma RS256 y exige los claims `sub`, `iss`, `aud` y `exp`. Conserva el esquema `Authorization: Bearer`, las respuestas exitosas y el HTTP 401 para credenciales inválidas, según el PR.
- **Acciones requeridas:** configurar `AUTH_JWT_PUBLIC_KEY`, `AUTH_JWT_ISSUER` y `AUTH_JWT_AUDIENCE` en el entorno de despliegue de la API. El emisor de tokens debe entregar JWT RS256 con los cuatro claims requeridos; los tokens legacy Base64 ya no satisfacen el contrato. Estas acciones se justifican por la configuración externa y las reglas de validación descritas en el PR.
- **PR integrado:** [#22 — API: verify JWT signatures for H-API-04](https://github.com/user-bcp-student17/ai-labs/pull/22)

## Evidencia y límites

- GitHub MCP resolvió la referencia inicial a `cb5379576a5310d4154b8978f90d73aa51e8b55d`. El commit es el merge del PR #21; por ser exactamente el límite inicial exclusivo, ese PR no pertenece al intervalo.
- GitHub MCP resolvió `main` a `d2fb14b3be80b44f80e7dd7126297d73150098d6`. La consulta del PR #22 confirmó `merged: true`, `merged_at: 2026-10-28T14:22:42Z`, `base.sha` igual al SHA inicial y `head.sha` igual al SHA final. El historial de `main` consultado por MCP contiene el commit final y sus commits precedentes hasta el límite, por lo que #22 queda dentro del intervalo.
- La búsqueda MCP de PR integrados desde `2026-10-27` devolvió únicamente el PR #22. La revisión de los detalles del PR confirma que el efecto y las acciones anteriores están documentados allí; no se incluyeron cambios por mera mención o estado cerrado.
- El PR reporta `python tools/lab.py test api`: 46 passed, 2 xfailed y cobertura total de 97.76% (94% para `app/security.py`). También indica que no se ejecutó integración con Auth y que `docker compose config --quiet` no pudo ejecutarse porque Docker no estaba instalado. Son resultados y límites reportados por el PR, no una validación independiente de estas notas.
