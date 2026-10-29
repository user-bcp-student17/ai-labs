# Hallazgos

| id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|---|
| H-API-01 | api | Filtros e inserciones SQL concatenan valores de entrada | Vulnerabilidad | Resuelto: se movieron las consultas dinamicas a `TaskRepository` y se enlazan los valores con parametros SQLite; pruebas con apostrofes cubren filtros e inserciones. | api/app/repositories.py:8-42, api/tests/test_api.py:42-72 | alta | Resuelto |
| H-API-02 | api | El propietario no queda ligado a la identidad autenticada | Vulnerabilidad | Pendiente: se rechazan propietarios distintos, pero `owner=""` se trata como ausente y permite crear con 201; el test de regresión estricto reproduce `201` en vez del `403` acordado. | api/app/routes.py:49; api/app/schemas.py:11-16; api/tests/test_api.py:120-148 | alta | Pendiente |
| H-API-03 | api | La carga usa el nombre de archivo recibido sin normalizar ni limitar tamaño o extensión | Vulnerabilidad | Pendiente: el validador acepta `requirements.txt:payload.txt`; en Windows el test de regresión estricto reproduce `201` en vez del `400` esperado. La extensión y el límite de tamaño sí se controlan. | api/app/upload_service.py:18-27,37-38; api/tests/test_api.py:202-241 | alta | Pendiente |
| H-API-04 | api | El token es Base64 con secreto hardcodeado y sin verificación de firma | Vulnerabilidad | Resuelto en API: verificación JWT RS256 con `sub`, `iss`, `aud` y `exp` obligatorios; la clave pública y parámetros se obtienen de configuración externa, sin fallback legacy. Integración con Auth queda pendiente de prueba con su emisor. | api/app/security.py:8-61; api/tests/test_api.py:20-93,332-421 | alta | Resuelto |
| H-API-05 | api | Rutas, reglas, SQLite y serialización están concentradas en un módulo | Refactor | Resuelto: rutas, autenticación, servicios de resumen, repositorio y carga quedaron separados en módulos; las pruebas de contrato de las cinco rutas pasan. | api/app/main.py:14,33-34; api/app/routes.py:33-82; api/app/services.py:5-29; api/tests/test_api.py:21-266 | media | Resuelto |
| H-API-06 | api | Tipado genérico, manejo amplio de excepciones, lógica anidada y proyección SQL repetida | Refactor | Resuelto: se agregaron modelos Pydantic de request/response, conversión legacy explícita, lógica de resumen plana, captura de errores específicos y mensajes genéricos. | api/app/schemas.py:6-58; api/app/security.py:11-20; api/app/services.py:17-29; api/app/routes.py:21-97; api/tests/test_api.py:66-263 | media | Resuelto |
| H-API-07 | api | Versiones de dependencias requieren revisión SCA | Vulnerabilidad | Reabierto: la auditoría de requisitos reportó advisories para `python-multipart 0.0.30` y Starlette `0.50.0`; requieren análisis y remediación separados. No se ocultó el resultado ni se amplió H-API-04. | api/requirements.txt:1,5; comando `python -m pip_audit -r requirements.txt` desde `api/` | baja | Pendiente |
| H-AUTH-01 | auth | Consulta de login construida por concatenacion SQL | Vulnerabilidad | Las credenciales se concatenan en la consulta de `LegacyDatabase`, lo que permite inyeccion SQL en `POST /auth/login`. Issue: ai-labs#25. | auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:32 | alta | Confirmado |
| H-AUTH-02 | auth | El token legacy es Base64 con secreto hardcodeado | Vulnerabilidad | `LegacyTokenUtil` firma el token con un secreto fijo en el codigo y lo codifica en Base64, por lo que cualquiera con el codigo puede forjarlo. Issue: ai-labs#26. | auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java:8,14 | alta | Confirmado |
| H-AUTH-03 | auth | Contraseñas de demostracion persistidas en texto claro | Vulnerabilidad | La tabla `legacy_users` guarda contraseñas en texto claro y siembra credenciales de demostracion. Issue: ai-labs#28. | auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:22-24 | media | Confirmado |
| H-AUTH-04 | auth | El campo `client` del login no se valida y los claims no tienen pruebas | Validacion | `LoginRequest` acepta `client` sin validarlo y la prueba solo cubre el caso feliz. Issue: user-bcp-student17/workshop-auth-backend-archive-taller-anterior-2#11. | auth/src/main/java/com/bcp/workshop/auth/LoginRequest.java:6; auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java:16 | media | Confirmado |

## Candidatos de discovery - API

### H-API-08 - Colision de archivos cargados por identidades distintas
- Estado: CANDIDATO
- Evidencia: `api/app/upload_service.py:31-39` valida el nombre y guarda en `Path(upload_dir) / filename`; la ruta `api/app/routes.py:66-76` obtiene la identidad, pero no la pasa al almacenamiento. El contrato de `POST /api/requirements` describe el archivo como asociado al usuario autenticado (`docs/ENDPOINTS.md:190-216`).
- Impacto: dos usuarios que carguen el mismo nombre comparten destino y la segunda carga puede reemplazar los bytes de la primera; puede provocar pérdida o contaminación de datos entre identidades.
- Prioridad propuesta: Media.
- Contrato potencialmente afectado: aislamiento por usuario y respuesta `201` de `POST /api/requirements`, en particular `owner`, `fileName` y `storedAt`.
- Como validarlo: con un directorio temporal, cargar el mismo nombre permitido con contenidos distintos usando dos identidades; comprobar si ambas respuestas apuntan al mismo destino y si la segunda carga reemplaza el contenido almacenado.

### H-API-09 - El rol autenticado no participa en la autorizacion
- Estado: CANDIDATO
- Evidencia: `api/app/security.py:18-25` extrae el rol, pero `ensure_owner_access` solo compara el nombre de usuario; las rutas protegidas dependen de la identidad en `api/app/routes.py:33-81` y no comprueban el rol.
- Impacto: si hay operaciones que deban restringirse por rol, cualquier identidad autenticada puede invocarlas; la matriz de permisos esperada no está definida en la evidencia revisada.
- Prioridad propuesta: Baja, pendiente de confirmar la política de roles.
- Contrato potencialmente afectado: autorización de `GET /api/tasks`, `POST /api/tasks`, `GET /api/summary`, `POST /api/requirements` y `GET /api/backend-health`.
- Como validarlo: acordar primero una matriz de permisos; después, probar cada ruta con identidades de cada rol y verificar respuestas permitidas o `403` conforme a esa matriz.

### H-API-10 - Conexion SQLite compartida entre solicitudes concurrentes
- Estado: CANDIDATO
- Evidencia: `api/app/main.py:20,33` crea una conexión con `check_same_thread=False` y la comparte mediante `TaskRepository`; `api/app/repositories.py:18-32` ejecuta y confirma escrituras en esa conexión sin sincronización explícita.
- Impacto: solicitudes concurrentes podrían interferir en transacciones o producir errores de base de datos; no se ha confirmado el comportamiento bajo carga concurrente.
- Prioridad propuesta: Media.
- Contrato potencialmente afectado: `POST /api/tasks` y la consistencia de las lecturas posteriores en `GET /api/tasks` y `GET /api/summary`.
- Como validarlo: ejecutar solicitudes concurrentes de creación contra una base SQLite temporal; verificar que todas las respuestas sean `201`, que no haya errores de base de datos y que las filas confirmadas coincidan con las solicitudes aceptadas.