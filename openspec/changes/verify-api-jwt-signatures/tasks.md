# Tasks

## 1. Caracterización previa de autenticación

- [x] 1.1 Añadir pruebas de caracterización de acceso válido para las cinco rutas protegidas, incluyendo identidad tomada de `sub`, `role` opcional y respuestas exitosas documentadas; verificar desde `api/` con `python -m pytest tests/test_api.py`.
- [x] 1.2 Añadir pruebas de caracterización para credenciales ausentes o malformadas, JWT legacy, firma inválida, claims requeridos ausentes o inválidos y expiración; verificar `401` y el cuerpo exacto `{"detail":"Invalid token"}` sin ejecutar la operación protegida con `python -m pytest tests/test_api.py`.
- [x] 1.3 Caracterizar con pruebas la falta de cada variable JWT, clave pública no utilizable, prioridad de `401` ante autorización ausente y PEM con `\\n`; verificar los status y cuerpos `401`/`503` definidos en la spec con `python -m pytest tests/test_api.py`.
- [x] 1.4 Añadir una prueba de regresión que confirme que los fallos de credencial o configuración no registran tokens, credenciales ni material de clave; verificar la salida capturada de logs con `python -m pytest tests/test_api.py`.

## 2. Verificación JWT incremental

- [x] 2.1 Ajustar únicamente la frontera compartida de autenticación en `api/app/security.py` para aceptar RS256 y validar firma, `sub`, `iss`, `aud` y `exp` mediante configuración externa; verificar los casos de aceptación y rechazo con `python -m pytest tests/test_api.py`.
- [x] 2.2 Mantener la clasificación de errores: credencial ausente o inválida como `401` y configuración incompleta o clave no utilizable como `503`, sin fallback Base64 ni exposición de valores; verificar las pruebas de errores y logs con `python -m pytest tests/test_api.py`.
- [x] 2.3 Verificar de forma integrada que las cinco rutas usan la identidad validada y conservan sus respuestas exitosas y autorización existente por `owner`; ejecutar `python -m pytest` desde `api/`.

## 3. Despliegue y contrato documentado

- [ ] 3.1 Confirmar que `compose.yaml` permite suministrar externamente `AUTH_JWT_PUBLIC_KEY`, `AUTH_JWT_ISSUER` y `AUTH_JWT_AUDIENCE`, sin agregar secretos versionados; verificar la configuración con `docker compose config --quiet`.
- [x] 3.2 Actualizar o confirmar en `docs/ENDPOINTS.md` los nombres de configuración y las respuestas `401`/`503`, sin tokens ni valores sensibles y sin cambiar las secciones de `auth/` y `web/`; verificar que el documento coincide con la spec.
- [x] 3.3 Ejecutar la suite completa del componente API desde `api/` con `python -m pytest` y confirmar que las pruebas de contrato de las cinco rutas y de autenticación pasan.
