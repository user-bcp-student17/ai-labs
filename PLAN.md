# Plan de corrección de ReqFlow

Plan compartido. Cada componente mantiene sus propios apartados. Los IDs vienen de `HALLAZGOS.md`; el estado de cada hallazgo se actualiza allí, no aquí.

## api

Propuesta únicamente: no se ha modificado código. `docs/ENDPOINTS.md` no existe, por lo que el contrato a preservar es el **contrato observado** de `HALLAZGOS.md` (sección api): rutas, métodos, nombres de campos (`createdAt`, `byStatus`, `highPriorityOpen`, `fileName`, `storedAt`, `size`, `requestedBy`, `status`, `body`) y códigos 200/201/401. Convenciones: solo `docs/GOOD_PRACTICES.md` (api) y las reglas de Clean Code de `AGENTS.md` (una responsabilidad por función, sin duplicación, sin anidamiento profundo —guard clauses—, sin literales mágicos).

### Estructura objetivo (api/app/)

| Módulo | Responsabilidad |
|---|---|
| `main.py` | Solo `create_app`: configura middleware, conexión y registra routers (conserva firma `create_app(db_path, upload_dir)` y `app = create_app()`). |
| `config.py` | Settings desde variables de entorno y constantes con nombre. |
| `security.py` | Verificación del token y dependencia `current_identity`. |
| `schemas.py` | Modelos Pydantic de request/response. |
| `repository.py` | Único lugar con SQL (parametrizado). |
| `services.py` | Reglas: autorización por identidad, resumen, subida de archivos. |
| `routes/` | Funciones de ruta delgadas (`tasks`, `requirements`, `health`). |

### Orden de ejecución propuesto

1. Pruebas de caracterización de todos los endpoints (antes de cualquier cambio, deben pasar sobre el código actual).
2. H-API-08 / H-API-09 / H-API-10 (separación en capas con comportamiento idéntico, base para los demás).
3. H-API-03 (SQL), H-API-02 (autorización), H-API-01 (token), H-API-04 (archivos), H-API-06 (errores), H-API-07 (CORS).
4. H-API-05 (dependencias) con evidencia del advisory.
5. Regresión completa con `python tools/lab.py test api` y registro en `docs/TESTING.md` (paso posterior). Meta: 85 % del código modificado; el gate de 85 % de toda la app se conserva sin cambiar umbrales.

Cada cambio propuesto va en un commit/PR revisable por separado (API → servicio → repositorio → seguridad).

---

### H-API-01 — Token Base64 con secreto embebido (alta)

- **Hallazgo:** H-API-01 en `HALLAZGOS.md` (api/app/main.py:14, api/app/main.py:19-23).
- **Problema:** el token se decodifica de Base64 y se confía en su contenido; el secreto es una constante del código. Cualquiera que lo conozca fabrica tokens de cualquier usuario o rol. No se valida firma, emisor ni audiencia.
- **Cambio propuesto:**
  - `security.py`: `verify_token(token) -> Identity` que valida **firma, emisor (`iss`), audiencia (`aud`) y expiración (`exp`)** de un JWT firmado (HS256), con claims requeridos `sub` (→ `username`), `role`, `exp`, `iss`, `aud`. Rechaza algoritmo no esperado (lista fija de algoritmos) y tokens sin claims obligatorios.
  - Modelo `Identity(username: str, role: str)` (Pydantic) en lugar de `dict[str, str]`; la dependencia sigue llamándose igual de cara a las rutas.
  - Guard clauses: cabecera ausente o sin esquema `Bearer` → 401; token inválido → 401 con `detail` genérico (`"Invalid token"`), detalle solo al log (ver H-API-06). Constantes `BEARER_PREFIX`, `JWT_ALGORITHMS`.
  - Configuración por entorno: `WORKSHOP_JWT_SECRET`, `WORKSHOP_JWT_ISSUER`, `WORKSHOP_JWT_AUDIENCE`. Sin valor por defecto real: la app falla al arrancar si falta el secreto salvo valores de prueba aislados en las pruebas.
  - Eliminar `LEGACY_SECRET`. El rol se conserva en `Identity` (hoy no se usa en las rutas).
- **Dependencia nueva (a justificar y aprobar):** `PyJWT` (versión fijada y revisada contra advisories al momento de instalar). Justificación: implementar JWS a mano con `hmac` y `base64` repite el riesgo que este hallazgo quiere eliminar. Si se rechaza, alternativa: HS256 con la biblioteca estándar (más código propio a probar).
- **Coordinación (fuera de AMBITO, sin tocarla):** hoy `auth` emite el token Base64 que `api` acepta. Cambiar solo `api` rompe el login → tareas. Requiere acordar con el componente `auth` (H-AUTH, "Token") emisor, audiencia, secreto compartido por entorno y claims, y revisar ambos consumidores (README §6). Las pruebas de `api` firman sus propios tokens de prueba y no dependen de `auth`. Pendiente: contrato de token acordado.
- **Archivos a tocar:** `api/app/security.py` (nuevo), `api/app/config.py` (nuevo), `api/app/main.py`, `api/requirements.txt` (si se aprueba PyJWT), `api/tests/`.
- **Prueba de caracterización previa:** (a) token Base64 legado válido → 200 en `/api/tasks`; (b) token con firma incorrecta/ malformado → 401; (c) token expirado → 401; (d) sin cabecera → 401. Se escribe sobre el código actual. Tras el cambio, (a) se invierte deliberadamente (token legado → 401) y se añaden: emisor incorrecto → 401, audiencia incorrecta → 401, algoritmo `none` → 401, claim faltante → 401, token válido → 200 con la identidad esperada.

### H-API-02 — El cliente elige el `owner` (alta)

- **Hallazgo:** H-API-02 (api/app/main.py:69, api/app/main.py:83, api/app/main.py:92).
- **Problema:** `owner` por query/body prevalece sobre la identidad: cualquier usuario autenticado lee o crea tareas de otro.
- **Cambio propuesto:** el servicio usa siempre `identity.username` (de `GOOD_PRACTICES`: "las consultas siempre usan `identity["username"]`, nunca un parámetro `owner` del cliente"). Para mantener el contrato observado (el parámetro `owner` y el campo `owner` del body existen y el frontend puede enviarlos): se **aceptan** pero solo se permite el propio usuario; si `owner` ≠ identidad → 403 con mensaje genérico, si es igual o ausente → comportamiento actual. Una sola función `resolve_owner(requested, identity)` (guard clause) reutilizada por `list_tasks`, `create_task` y `summary` (elimina la duplicación de `requested_owner = owner or ...`). `summary` devuelve `owner` = identidad.
- **Decisión pendiente de aprobación humana:** 403 vs. ignorar silenciosamente el `owner` ajeno; y si el rol `TRAINER` debe poder ver otros owners (no está en `GOOD_PRACTICES`, por tanto **no** se asume; el plan es solo identidad).
- **Archivos a tocar:** `api/app/services.py` (nuevo), `api/app/routes/tasks.py` (nuevo), `api/app/main.py`, `api/tests/`.
- **Prueba de caracterización previa:** con token de `student`, `GET /api/tasks?owner=trainer` y `GET /api/summary?owner=trainer` hoy devuelven los datos de `trainer` (documenta el riesgo); `POST /api/tasks` con `owner: "trainer"` crea la tarea a nombre de `trainer`. Tras el cambio: los tres → 403; sin `owner` o con el propio → igual que hoy (2 tareas seed para `student`).

### H-API-03 — SQL concatenado (alta)

- **Hallazgo:** H-API-03 (api/app/main.py:70, api/app/main.py:84, api/app/main.py:87, api/app/main.py:93).
- **Problema:** valores del cliente concatenados en `SELECT`/`INSERT`: inyección SQL y errores 500 con comillas simples.
- **Cambio propuesto:** `repository.py` con `list_by_owner(owner)`, `insert(task)`, `get_by_id(id)` y `list_status_priority_by_owner(owner)`, todas con placeholders `?` y tupla de parámetros. Las rutas y servicios no contienen SQL. La siembra inicial y el `CREATE TABLE` pasan a una función `init_schema` del repositorio (constantes SQL con nombre, parametrizadas donde haya valores). Sin cambio de esquema ni de formato de respuesta (`createdAt` sigue mapeado desde `created_at` en el serializador Pydantic).
- **Archivos a tocar:** `api/app/repository.py` (nuevo), `api/app/main.py`, `api/tests/`.
- **Prueba de caracterización previa:** título con comilla simple (`"O'Neil"`) hoy devuelve 500 (documenta el defecto); con `title`/`owner` con metacaracteres SQL se comprueba que tras el cambio se guarda/consulta como texto literal y no altera otras filas; se fija el comportamiento de orden por `id` y de `createdAt`.

### H-API-04 — Carga de archivos sin normalizar nombre, extensión ni tamaño (alta)

- **Hallazgo:** H-API-04 (api/app/main.py:109-112).
- **Problema:** `file.filename` del cliente se usa como ruta: path traversal/sobrescritura, extensión libre, contenido íntegro en memoria sin tope, y se expone la ruta interna.
- **Cambio propuesto:** servicio `store_requirement(upload, identity)` con funciones pequeñas: `sanitize_filename` (solo el nombre base, sin separadores ni caracteres de control; vacío → 400), `validate_extension` (lista blanca en una constante `ALLOWED_EXTENSIONS`), `read_with_limit` (lectura por bloques con tope `MAX_UPLOAD_BYTES`; excedido → 413) y comprobación de que la ruta resuelta queda dentro de `upload_dir`. La respuesta mantiene los campos `owner`, `fileName`, `storedAt`, `size`; `fileName` será el nombre normalizado.
- **Decisiones pendientes de aprobación:** lista concreta de extensiones (propuesta inicial: `.txt`, `.md`, `.pdf`, `.docx`), tope de tamaño (propuesta: 5 MiB), política ante nombre existente (hoy sobrescribe; propuesta: conservar, o prefijo único) y si `storedAt` debe devolver solo el nombre relativo en vez de la ruta absoluta del servidor. Estos valores no están en `GOOD_PRACTICES`, se proponen y requieren aprobación.
- **Archivos a tocar:** `api/app/services.py` (o `uploads.py`), `api/app/routes/requirements.py`, `api/app/config.py` (constantes), `api/tests/`.
- **Prueba de caracterización previa:** subida de `requirements.txt` → 201 con `fileName`, `size` y archivo en `upload_dir` (ya cubierto por `test_uploads_requirement`); añadir: nombre con `../` hoy se acepta y escribe fuera/ dentro de la ruta (documentar sobre `tmp_path`); archivo grande hoy se acepta. Tras el cambio: nombre con `../` → archivo dentro de `upload_dir` con nombre base o 400; extensión no permitida → 400/415; archivo mayor que el tope → 413; ningún archivo escrito fuera de `upload_dir`.

### H-API-05 — Dependencias `urllib3 2.5.0` y `python-multipart 0.0.21` (media)

- **Hallazgo:** H-API-05 (api/requirements.txt:4, api/requirements.txt:5).
- **Problema:** versiones con advisories (python-multipart ≤0.0.21: CVE-2026-24486; urllib3 2.5.0: corregido en ≥2.6.0; CVE exactos por confirmar).
- **Cambio propuesto:** confirmar advisories con `pip-audit` o fuente oficial (evidencia en `HALLAZGOS.md`), subir a la versión corregida más baja compatible (`python-multipart` ≥0.0.22; `urllib3` ≥2.6.0, o la que indique el advisory), no silenciar advisories. Se mantienen fijadas (`==`) como hoy y se comprueba compatibilidad con `fastapi==0.128.2` y `httpx==0.28.1`. No se añaden dependencias nuevas por este hallazgo.
- **Archivos a tocar:** `api/requirements.txt` (`api/requirements-dev.txt` solo si `httpx` exige un ajuste).
- **Prueba de caracterización previa:** suite completa verde antes del cambio (línea base) y de nuevo después; prueba de subida multipart (H-API-04) y `backend-health` (usa `urllib3`) como cobertura del uso de ambas librerías. Registrar `pip-audit` antes/después como evidencia (sin inventar resultados).

### H-API-06 — Errores exponen detalle interno (media)

- **Hallazgo:** H-API-06 (api/app/main.py:26, api/app/main.py:121).
- **Problema:** `str(error)` se devuelve al cliente en el 401 y en `backend-health`.
- **Cambio propuesto:** `HTTPException` con mensajes genéricos (`"Invalid token"`); el detalle va a `logging` del servidor sin secretos. En `backend-health` se capturan excepciones concretas de `urllib3` (`HTTPError`) en vez de `Exception`; el contrato observado se conserva (200 con `status: 0`), pero `body` pasa a un texto genérico (p. ej. `"Backend unavailable"`). Constante `HEALTH_TIMEOUT_SECONDS` en lugar de `3.0` y reutilización de un `PoolManager` en lugar de crear uno por petición.
- **Archivos a tocar:** `api/app/security.py`, `api/app/routes/health.py` (nuevo), `api/app/config.py`, `api/tests/`.
- **Prueba de caracterización previa:** token basura → 401 con `detail` que hoy empieza por `"Invalid token: "` + texto de excepción; `backend-health` con `AUTH_HEALTH_URL` inalcanzable → 200, `status` 0, `body` con texto de la excepción. Tras el cambio: `detail`/`body` genéricos, sin texto de excepción, y el estado 200 / `status` 0 se mantiene. (Con `urllib3` simulado para no depender de la red.)

### H-API-07 — CORS abierto con credenciales (media)

- **Hallazgo:** H-API-07 (api/app/main.py:48-54).
- **Problema:** `allow_origins=["*"]` junto con `allow_credentials=True`, métodos y cabeceras abiertos.
- **Cambio propuesto:** orígenes desde `WORKSHOP_CORS_ORIGINS` (lista separada por comas; valor por defecto el origen del frontend de desarrollo `http://localhost:4200`, según README), métodos limitados a `GET`, `POST`, `OPTIONS` y cabeceras a `Authorization`, `Content-Type`. Constantes con nombre en `config.py`. Cualquier origen no listado no recibe cabeceras CORS.
- **Archivos a tocar:** `api/app/config.py`, `api/app/main.py`, `api/tests/`.
- **Prueba de caracterización previa:** petición `OPTIONS` con `Origin` arbitrario hoy recibe `Access-Control-Allow-Origin`; tras el cambio solo el origen configurado la recibe. Pendiente: confirmar con `web` el origen real en compose (sin leer ese código).

### H-API-08 — Todo en un solo archivo (media)

- **Hallazgo:** H-API-08 (api/app/main.py:29-121).
- **Problema:** `create_app` mezcla esquema, siembra, rutas, SQL, reglas y serialización.
- **Cambio propuesto:** la estructura objetivo descrita arriba (rutas → servicio → repositorio). Se hace como refactor sin cambio de comportamiento, primero con la suite de caracterización en verde. `create_app(db_path, upload_dir)` conserva su firma; la conexión y el directorio de subida se inyectan al repositorio/servicio mediante dependencias de FastAPI.
- **Archivos a tocar:** `api/app/main.py`, nuevos `config.py`, `security.py`, `schemas.py`, `repository.py`, `services.py`, `routes/`.
- **Prueba de caracterización previa:** conjunto completo sobre los 5 endpoints (lista, creación, resumen con `byStatus` y `highPriorityOpen` HIGH no DONE/ARCHIVED, subida, `backend-health` con `urllib3` simulado, 401 sin token) con salida exacta de JSON; debe pasar igual antes y después del movimiento de código.

### H-API-09 — Calidad: `dict`/`Any`, excepciones amplias, anidamiento, duplicación (baja)

- **Hallazgo:** H-API-09 (api/app/main.py:25, api/app/main.py:78-83, api/app/main.py:94-106, api/app/main.py:101-103, api/app/main.py:119-121).
- **Problema:** sin Pydantic; `except Exception`; `summary()` con tres `if` anidados; acceso repetido a `response[...]`; literales mágicos.
- **Cambio propuesto:**
  - Modelos Pydantic en `schemas.py`: `TaskCreate` (`title`, `description`, `status`, `priority`, `owner` opcional; `status` y `priority` como `Literal`/`Enum` con los valores observados: `TODO`, `IN_PROGRESS`, `DONE`, `ARCHIVED` / `HIGH`, `MEDIUM`, `LOW`; defaults `TODO` y `MEDIUM`), `TaskResponse` (alias `createdAt`), `SummaryResponse`, `UploadResponse`, `HealthResponse`, `Identity`.
  - `summary`: una función `is_open_high_priority(row)` con condición combinada o retorno anticipado y `collections.Counter` para `byStatus`; constantes `CLOSED_STATUSES`, `HIGH_PRIORITY`.
  - Excepciones concretas; `as_task` sustituido por `TaskResponse.model_validate`.
  - Los payloads inválidos pasarían a 422 (validación Pydantic) en vez de aceptarse como texto. **Es un cambio de comportamiento sobre entradas hoy "aceptadas"**: a validar con el frontend actual (que envía los valores observados) y registrar como riesgo si hay discrepancias. Los valores permitidos de `status`/`priority` salen de la siembra del código; se confirmarán antes de restringir.
- **Archivos a tocar:** `api/app/schemas.py` (nuevo), `api/app/services.py`, `api/app/routes/*`, `api/tests/`.
- **Prueba de caracterización previa:** `summary` con combinaciones de estado/prioridad (HIGH+TODO cuenta; HIGH+DONE y HIGH+ARCHIVED no; MEDIUM no); creación con defaults (`TODO`/`MEDIUM`); forma exacta de la respuesta (`createdAt` presente, sin `created_at`).

### H-API-10 — Conexión SQLite compartida y ciclo de vida (baja)

- **Hallazgo:** H-API-10 (api/app/main.py:35, api/app/main.py:123-124, api/app/main.py:130).
- **Problema:** una conexión con `check_same_thread=False` compartida sin sincronización; `on_event("shutdown")` en desuso; `app = create_app()` ejecuta efectos (crear DB/carpetas) al importar.
- **Cambio propuesto:** reemplazar `on_event` por `lifespan` de FastAPI que cierra la conexión; una conexión por petición mediante dependencia (o `Lock` si se conserva la compartida; se decide al implementar y se justifica); mantener `app = create_app()` a nivel de módulo porque `uvicorn app.main:app` lo usa (comportamiento observado), pero sin efectos fuera de `create_app`.
- **Archivos a tocar:** `api/app/main.py`, `api/app/repository.py`, `api/tests/`.
- **Prueba de caracterización previa:** `create_app` con `tmp_path` crea DB y carpeta de subida, siembra 3 tareas y cierra la conexión al terminar el `TestClient`; petición concurrente simple (hilos) sin errores de SQLite.

---

### Aprobación humana registrada (api)

Respuesta literal del usuario a la solicitud de aprobación, 2026-11-02 (sesión de implementación):

- IDs aprobados: `H-API-01, H-API-02, H-API-03, H-API-04, H-API-10, H-API-08, H-API-09, H-API-07, H-API-06, H-API-05`.
- Dependencia `PyJWT` (H-API-01): **Aprobada**.
- `owner` ajeno (H-API-02): **403 si owner distinto a la identidad**.
- Archivos (H-API-04: extensiones, tamaño, nombre existente, `storedAt`): **Pendiente** → no se implementan esas decisiones; H-API-04 queda sin implementar hasta que se decidan.
- Otras decisiones (contrato de token con `auth`, origen CORS, 422 en H-API-09): **Pendiente** → se implementa solo la parte que no exige decidirlas (ver "Desviaciones del plan").

### Registro de ejecuciones (api)

Comandos con cwd `api/` (venv `api/.venv`, Python 3.14.7) salvo indicación. Resultados reales de esta sesión (2026-11-02).

| # | IDs | Comando | Resultado |
|---|---|---|---|
| 1 | línea base | `python -m pytest --cov=app` | 4 passed, cobertura 91 % (antes de cambiar código) |
| 2 | caracterización (todos) | `python -m pytest` (código original, tests/test_characterization.py nuevo) | 24 passed |
| 3 | H-API-08/09/10 correcciones | `pytest tests/test_refactor_structure.py` antes del cambio | 6 failed |
| 4 | H-API-08/09/10 | `pytest` tras el refactor | 30 passed |
| 5 | H-API-03 | `pytest tests/test_sql_parameterization.py` antes / después | 4 failed / 33 passed (suite completa) |
| 6 | H-API-02 | `pytest tests/test_authorization.py` antes / después | 4 failed, 2 passed (los 2 conservan comportamiento) / 37 passed (suite completa) |
| 7 | H-API-01 y parte de H-API-06 | `pytest tests/test_token_verification.py` antes / después | 5 failed, 17 passed (los rechazos ya se cumplían con el token legado) / 58 passed con los 3 tests de `test_api.py` actualizados a JWT |
| 8 | H-API-06 | `pytest tests/test_error_handling.py` antes / después | 1 failed, 1 passed / pasa |
| 9 | H-API-07 | `pytest tests/test_cors.py` antes / después | 5 failed, 1 passed / 65 passed (suite completa, cobertura 100 %) |
| 10 | H-API-05 | `pytest tests/test_dependencies.py` antes / después | 3 failed, 2 passed (versión instalada ya subida) / 70 passed |
| 11 | H-API-05 | `python -m pip_audit -r requirements.txt --disable-pip --no-deps` antes / después | 22 vulnerabilidades en 2 paquetes (urllib3 2.5.0, python-multipart 0.0.21) / "No known vulnerabilities found" |
| 12 | todos menos H-API-04 | `python tools/lab.py test api` (desde la raíz) | 70 passed, cobertura total 100 % (gate 85 % cumplido); `pip check`: sin conflictos |

Cobertura: 231 sentencias, 0 sin cubrir, 12 ramas, 0 parciales (`--cov-branch` en la corrida #9). Cubre todo el código modificado; el método es la cobertura total de `app` porque el diff reescribe todo `api/app`. No se ejecutó `docker compose` ni la integración `web`/`auth` (pendiente).

### Desviaciones del plan (api)

- **H-API-04 no implementado:** sus decisiones quedaron "Pendiente" en la aprobación. Su código solo se movió a `services.store_requirement` sin endurecerlo (sigue vulnerable).
- **Orden:** 08, 09 y 10 se hicieron en una sola reestructuración (un cambio coherente), con sus pruebas de corrección escritas antes y fallando (corrida #3). SQL/seguridad se movieron al repositorio/módulo de seguridad en ese paso y se corrigieron después (H-API-03, H-API-02, H-API-01).
- **H-API-01:** requiere el encabezado `Authorization: Bearer <jwt>`; un token sin esquema `Bearer` ahora se rechaza (antes se aceptaba). El emisor (`auth`) y el secreto compartido no están acordados: `iss`/`aud` tienen valores provisionales `reqflow-auth`/`reqflow-api` y `WORKSHOP_JWT_SECRET` es obligatorio (sin él, 500). Hasta coordinarlo, el login real de `auth` → `api` no funciona de extremo a extremo (no probado). No se modificó compose ni `auth`.
- **H-API-09:** `status`/`priority` quedan como `str` libres (la restricción con 422 estaba pendiente). Sí cambia que valores no string (p. ej. listas o números) ahora dan 422 en vez de convertirse con `str()`.
- **H-API-06:** `backend-health` sigue creando un único `PoolManager` por proceso (en vez de uno por petición) y decodifica con `errors="replace"`.
- **H-API-10:** se eligió una conexión por petición (no `Lock`, no `lifespan`): no queda nada que cerrar al apagar.
- **H-API-05:** versiones mínimas sin advisories con `pip-audit`: `urllib3` 2.8.0 y `python-multipart` 0.0.31; `PyJWT==2.15.1` añadido (aprobado). Pip-audit solo se instaló en el venv (no está en requirements).
- **Pruebas:** los 3 tests de `api/tests/test_api.py` pasan a firmar JWT (inversión deliberada prevista en el plan); `api/tests/__init__.py` y `conftest.py` nuevos. Se eliminaron de la caracterización los 5 tests de "riesgo conocido" (owner ajeno ×2, comilla en título, CORS abierto, detalle del 401) al convertirse en pruebas de corrección.
- **Sin evidencias** de aprobación humana del diff final: la revisión del código queda pendiente.

### Riesgos y decisiones pendientes (api)

| Pendiente | Hallazgo | Responsable |
|---|---|---|
| ~~Aprobación humana del plan y de la dependencia `PyJWT`~~ → aprobada el 2026-11-02 (ver "Aprobación humana registrada") | H-API-01 | Revisión humana |
| Contrato de token acordado con `auth` (emisor, audiencia, secreto por entorno, claims) | H-API-01 | Coordinación `auth` ↔ `api` |
| Política ante `owner` ajeno (403 vs. ignorar) y rol privilegiado | H-API-02 | Revisión humana |
| Extensiones permitidas, tamaño máximo, nombre existente, forma de `storedAt` | H-API-04 | Revisión humana |
| CVE exactos y versiones mínimas corregidas | H-API-05 | Confirmar con advisory/`pip-audit` |
| Origen CORS real del frontend en compose | H-API-07 | Coordinación con `web` (sin leer su código) |
| Valores permitidos de `status`/`priority` y 422 para entradas inválidas | H-API-09 | Revisión humana |
| `docs/ENDPOINTS.md` (contrato acordado) aún no existe | todos | Paso posterior |

## Item: H-API-04 — Carga segura de archivos (api)

Esta propuesta actualiza el alcance de H-API-04 sin borrar el plan histórico
anterior. El hallazgo sigue **Pendiente**. Seleccionar el item para planificar
no constituye aprobación de las decisiones ni autorización para implementar.

**Problema y evidencia actual.** La ruta de `POST /api/requirements` delega
la subida al servicio (`api/app/routes/requirements.py:11`). El servicio usa
el nombre recibido como ruta, lee el archivo completo en memoria y lo escribe
sin restricciones (`api/app/services.py:38`). Esto permite traversal,
sobrescrituras, consumo excesivo de recursos y divulgación de la ruta del
servidor. El resultado existente de traversal y el `xfail` estricto están
registrados en `docs/TESTING.md`; no se afirma una nueva ejecución aquí.

**Contrato y alcance.** Se conserva el método, la ruta, la autenticación y
el campo multipart `file`, así como el 201 y los campos `owner`, `fileName`,
`storedAt` y `size` para archivos válidos. El contrato observado documentado
en `docs/ENDPOINTS.md` admite nombres inseguros, cualquier extensión y tamaño
y sobrescrituras; corregir este item requiere restringir expresamente esos
comportamientos. Las nuevas respuestas de error y cualquier cambio en el valor
de `storedAt` son propuestas, no un contrato acordado. Mantener el valor actual
de `storedAt` conserva la compatibilidad, pero deja pendiente la exposición
de la ruta interna que también forma parte del hallazgo.

**Cambio propuesto, sujeto a decisión humana.**

1. Validar y normalizar el nombre con una función de responsabilidad única:
   rechazar nombres vacíos, separadores `/` y `\`, rutas absolutas,
   componentes `.` o `..`, caracteres de control y nombres no válidos para
   el almacenamiento. No utilizar directamente el nombre del cliente para
   abrir una ruta; comprobar el confinamiento en el directorio configurado
   y prevenir escapes mediante enlaces simbólicos y carreras al crear el
   archivo. Propuesta de error genérico: 400.
2. Aplicar una lista explícita de extensiones permitidas, comparadas sin
   distinguir mayúsculas. Propuesta inicial: `.txt`, `.md`, `.pdf` y
   `.docx`; rechazar otras extensiones y nombres sin extensión con 415.
   Son valores propuestos, no aprobados.
3. Limitar los bytes efectivamente recibidos con lectura por bloques, sin
   `read()` del archivo completo, y no publicar un archivo incompleto cuando
   se supere el máximo o falle la escritura. Propuesta inicial: 5 MiB,
   aceptando exactamente el límite y rechazando un byte adicional con 413.
   Evaluar también el límite de la petición multipart antes o durante su
   procesamiento: limitar solo la lectura de `UploadFile` no demuestra que
   el parser haya evitado previamente el consumo de recursos.
4. Propuesta para colisiones: no sobrescribir; responder 409 sin modificar
   el archivo existente, incluso si pertenece a otro usuario. Usar creación
   atómica para evitar carreras. La política de almacenamiento entre usuarios
   y el tratamiento de archivos ya existentes necesitan decisión.
5. Propuesta para `storedAt`: devolver una referencia relativa sin ruta
   interna; mantener los nombres y tipos de los campos de respuesta.
   Coordinar su compatibilidad con los consumidores sin leer ni modificar
   otros componentes. El cambio de valor, errores y restricciones debe
   acordarse antes de actualizar `docs/ENDPOINTS.md`.

Las decisiones sobre extensiones, tamaño, colisiones y `storedAt` permanecen
pendientes, como consta en la aprobación anterior. También requieren decisión
los códigos propuestos, la política exacta de nombres y el aislamiento entre
usuarios. Registrar aprobación humana y contrato acordado antes de cambiar
código; no introducir dependencias nuevas sin justificar y aprobar.

**Aprobación humana posterior (2026-11-02).** El usuario respondió: «Apruebo
implementar el apartado H-API-04», aceptó `.txt`, `.md`, `.pdf`, `.docx`,
el máximo de 5 MiB, el rechazo de colisiones con 409 sin sobrescritura
entre usuarios, `storedAt` como referencia relativa y los códigos propuestos
400/415/413/409. No agregó condiciones adicionales. Esta decisión reemplaza
los pendientes anteriores de esas políticas; la compatibilidad con los
consumidores externos sigue sin verificar.

**Ejecuciones posteriores (api, H-API-04; cwd `api/`).**
Caracterización previa: `.\.venv\Scripts\python.exe -m pytest
tests\test_endpoints_contract.py -k "post_requirements" -rx`: código 0,
10 aprobadas y 1 `xfail`. Corrección previa: `.\.venv\Scripts\python.exe
-m pytest tests\test_upload_security.py -q --tb=no`: código 1, 21 fallidas
y 3 aprobadas. Después: `.\.venv\Scripts\python.exe -m pytest -o addopts=''
tests\test_upload_security.py tests\test_endpoints_contract.py -k
"post_requirements or upload_security" -q`: código 0, 38 aprobadas.
Regresión completa y cobertura: ver la actualización H-API-04 de
`docs/TESTING.md` (162 aprobadas; 290/293 líneas modificadas cubiertas).

**Archivos previstos.** `api/app/services.py` para las reglas y escritura;
`api/app/config.py` para constantes o configuración aprobada;
`api/app/routes/requirements.py` solo si hace falta adaptar la respuesta
HTTP; `api/tests/test_endpoints_contract.py` y, si conviene, un archivo
específico en `api/tests/` para pruebas. En la fase de documentación,
actualizar solo las secciones de api de `docs/ENDPOINTS.md` y
`docs/TESTING.md`; registrar la resolución en `HALLAZGOS.md` únicamente
después de verificarla. No se modifica ninguno de esos contratos en este paso.

**Pruebas antes de tocar código.**

- Ejecutar la caracterización existente en `api/tests/test_endpoints_contract.py:230`
  y `api/tests/test_characterization.py:97`: archivo válido, 201, campos,
  tamaño y bytes persistidos. Conservar evidencia de los casos observados
  sin extensión y nombre repetido; si se acuerda restringirlos, cambiar sus
  expectativas explícitamente y documentar el cambio, sin ocultar el riesgo.
- Ejecutar la prueba de traversal existente en
  `api/tests/test_endpoints_contract.py:297` y registrar su `xfail`.
  Antes de corregir, escribir pruebas de seguridad que exijan confinamiento
  ante rutas relativas y absolutas, ambos separadores y enlaces simbólicos;
  documentar sus fallos reales sobre el código actual. Usar únicamente
  directorios temporales aislados.
- Escribir pruebas para extensión permitida y prohibida, sin extensión y
  mayúsculas; tamaño cero, exactamente el máximo y máximo más un byte;
  fallos de lectura/escritura sin archivo parcial; colisiones secuenciales
  y concurrentes, también entre identidades. Las expectativas concretas
  dependen de las decisiones anteriores.
- Tras implementar, retirar el `xfail` solo cuando la prueba de seguridad
  pase; verificar respuestas genéricas, que no se escriba fuera del destino
  y que no se sobrescriban archivos según la política aprobada. Ejecutar la
  suite de api con cwd `api/`, conservar el gate global existente y medir
  por separado la cobertura del código modificado con meta mínima de 85%.
  Registrar comandos y resultados reales en `docs/TESTING.md`.
