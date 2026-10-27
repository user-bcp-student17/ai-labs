# Contratos de endpoints

## API

### Estado del contrato

- **Observado en el código:** las cinco operaciones descritas abajo, sus campos y los status indicados como actuales. Las respuestas `401` y `403` usan `{"detail":"..."}`; los errores de validación FastAPI usan `{"detail":[...]}`.
- **Acordado:** se espera `403` para un `owner` explícito distinto del usuario autenticado y se permiten cargas `.txt` de hasta 1 MiB, con `400` para nombre/extensión rechazados y `413` por exceso de tamaño. El comportamiento actual no satisface completamente esos acuerdos para `owner=""` ni para nombres con `:`; ver riesgos por endpoint y H-API-02/H-API-03 en `HALLAZGOS.md`.
- **Autenticación observada:** todas las rutas requieren `Authorization: Bearer <token>`. El token debe ser Base64 de UTF-8 con cuatro partes separadas por `|`: `username|role|expUnix|secreto-legacy`; `expUnix` es una expiración Unix en segundos. El secreto se compara con un valor fijo embebido en API y no se publica aquí. No es un JWT firmado; `role` se lee pero no se usa para autorizar rutas. No usar este mecanismo como autenticación segura de producción. La migración JWT sigue pendiente (H-API-04).
- Los ejemplos usan `student` como identidad de muestra. El token es un marcador: debe sustituirse por un token que acepte la implementación actual. No es una credencial ejecutable.

### `GET /api/tasks`

1. **Qué hace:** devuelve las tareas del usuario autenticado para consultar su trabajo.

2. **Autenticación:** requerida. Header exacto: `Authorization: Bearer <token>`.

3. **Request:** no lleva body.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `owner` (query) | string | No | Filtro solicitado. Si se omite o es vacío se usa el username del token; un valor distinto no está autorizado. |

Ejemplo completo:

```http
GET /api/tasks?owner=student HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token>
```

4. **Response exitosa:** `200 OK`.

| Campo | Tipo | Descripción |
|---|---|---|
| raíz | array de objetos | Tareas del propietario autenticado; puede ser `[]`. |
| `id` | integer | Identificador de la tarea. |
| `title` | string | Título. |
| `description` | string | Descripción. |
| `status` | string | Estado guardado, sin conjunto de valores restringido por el schema. |
| `owner` | string | Username propietario. |
| `priority` | string | Prioridad guardada, sin conjunto de valores restringido por el schema. |
| `createdAt` | string | Fecha/hora de creación almacenada, en el formato producido por SQLite. |

Ejemplo completo (la fecha/hora e IDs dependen de los datos):

```json
[
  {
    "id": 1,
    "title": "Refactor login",
    "description": "Separar responsabilidades en frontend",
    "status": "TODO",
    "owner": "student",
    "priority": "HIGH",
    "createdAt": "2026-10-26 10:15:30"
  }
]
```

5. **Errores:**

| Status | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token inválido, malformado o vencido. | `{"detail":"Invalid token"}` |
| `403 Forbidden` | `owner` no vacío distinto del username autenticado. | `{"detail":"Owner access denied"}` |
| `500 Internal Server Error` | Fallo inesperado, por ejemplo de SQLite. El formato de error interno no está definido por esta ruta; ejemplo del servidor ASGI por defecto: `Internal Server Error` (texto plano). | `Internal Server Error` |

6. **Notas de seguridad:** el repositorio filtra por la identidad derivada del token y `ensure_owner_access` rechaza otro propietario. Sin embargo, el handler evalúa `owner or username`: `owner=` vacío se interpreta como omitido, no como un valor explícito que deba rechazarse. El token Base64 no demuestra integridad criptográfica. Referencias: `api/app/routes.py:32-41`, `api/app/security.py:11-25`, `api/app/repositories.py:8-13`.

### `POST /api/tasks`

1. **Qué hace:** registra una tarea para el usuario autenticado.

2. **Autenticación:** requerida. Header exacto: `Authorization: Bearer <token>`.

3. **Request:** JSON object. Todos los campos tienen defaults y son opcionales.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `title` | string | No | Título; default `""`. |
| `description` | string | No | Descripción; default `""`. |
| `status` | string | No | Estado; default `"TODO"`. No hay enum en el schema. |
| `priority` | string | No | Prioridad; default `"MEDIUM"`. No hay enum en el schema. |
| `owner` | string o null | No | Propietario solicitado; si se omite o es vacío se usa el username autenticado. Un valor distinto no está autorizado. |

Los valores enviados para esos campos se convierten a string con la conversión Python `str()`; en `owner`, esto también sucede si se envía explícitamente `null`.

Ejemplo completo:

```http
POST /api/tasks HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token>
Content-Type: application/json

{"title":"Add tests","description":"Improve coverage","status":"TODO","priority":"HIGH","owner":"student"}
```

4. **Response exitosa:** `201 Created`.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Identificador asignado. |
| `title` | string | Título guardado. |
| `description` | string | Descripción guardada. |
| `status` | string | Estado guardado. |
| `owner` | string | Username propietario autenticado. |
| `priority` | string | Prioridad guardada. |
| `createdAt` | string | Fecha/hora de creación almacenada por SQLite. |

Ejemplo completo (ID y fecha/hora dependen de la base de datos):

```json
{
  "id": 4,
  "title": "Add tests",
  "description": "Improve coverage",
  "status": "TODO",
  "owner": "student",
  "priority": "HIGH",
  "createdAt": "2026-10-26 10:15:30"
}
```

5. **Errores:**

| Status | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token inválido, malformado o vencido. | `{"detail":"Invalid token"}` |
| `403 Forbidden` | `owner` efectivo distinto del username autenticado. | `{"detail":"Owner access denied"}` |
| `422 Unprocessable Entity` | El body no es un objeto JSON que pueda validarse como request, o el JSON está malformado. Los detalles dependen del error de validación. | `{"detail":[{"type":"model_attributes_type","loc":["body"],"msg":"Input should be a valid dictionary or object to extract fields from","input":[]}]}` |
| `500 Internal Server Error` | Fallo inesperado, por ejemplo de SQLite. El formato interno no es un contrato estable; ejemplo del servidor ASGI por defecto: `Internal Server Error` (texto plano). | `Internal Server Error` |

6. **Notas de seguridad:** el propietario efectivo se compara con el username autenticado y las consultas usan parámetros SQL. El riesgo pendiente H-API-02 es que `owner: ""` cae al username y se crea la tarea (en lugar de responder `403` como se acordó). El campo `role` del token no aplica permisos y el token no tiene firma verificable. Referencias: `api/app/routes.py:43-52`, `api/app/schemas.py:6-29`, `api/app/security.py:23-25`, `api/app/repositories.py:15-25`.

### `GET /api/summary`

1. **Qué hace:** resume el volumen y estado de las tareas del usuario autenticado.

2. **Autenticación:** requerida. Header exacto: `Authorization: Bearer <token>`.

3. **Request:** no lleva body.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `owner` (query) | string | No | Propietario solicitado. Si se omite o es vacío se usa el username del token; un valor distinto no está autorizado. |

Ejemplo completo:

```http
GET /api/summary?owner=student HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token>
```

4. **Response exitosa:** `200 OK`.

| Campo | Tipo | Descripción |
|---|---|---|
| `owner` | string | Username resumido. |
| `total` | integer | Número total de tareas. |
| `byStatus` | object de string a integer | Conteo por cada valor de `status` almacenado. |
| `highPriorityOpen` | integer | Tareas `HIGH` cuyo estado no es `DONE` ni `ARCHIVED`. |

Ejemplo completo:

```json
{
  "owner": "student",
  "total": 2,
  "byStatus": {
    "TODO": 1,
    "IN_PROGRESS": 1
  },
  "highPriorityOpen": 1
}
```

5. **Errores:**

| Status | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token inválido, malformado o vencido. | `{"detail":"Invalid token"}` |
| `403 Forbidden` | `owner` no vacío distinto del username autenticado. | `{"detail":"Owner access denied"}` |
| `500 Internal Server Error` | Fallo inesperado, por ejemplo de SQLite. El formato interno no es un contrato estable; ejemplo del servidor ASGI por defecto: `Internal Server Error` (texto plano). | `Internal Server Error` |

6. **Notas de seguridad:** el resumen se calcula sobre las tareas del propietario extraído de la identidad y se rechaza otro propietario. `owner=` vacío se trata como omitido por el fallback actual. La identidad procede del token Base64 legacy, no de un JWT verificado. Referencias: `api/app/routes.py:54-63`, `api/app/services.py:18-31`, `api/app/security.py:11-25`.

### `POST /api/requirements`

1. **Qué hace:** guarda un archivo de requisitos de texto asociado al usuario autenticado.

2. **Autenticación:** requerida. Header exacto: `Authorization: Bearer <token>`.

3. **Request:** `multipart/form-data`.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `file` | archivo multipart | Sí | Archivo con nombre terminado en `.txt` (la extensión se compara sin distinguir mayúsculas) y contenido de hasta 1 MiB inclusive. |

Ejemplo completo (curl genera el boundary multipart):

```bash
curl -X POST http://localhost:8000/api/requirements \
  -H 'Authorization: Bearer <token>' \
  -F 'file=@requirements.txt;type=text/plain'
```

4. **Response exitosa:** `201 Created`.

| Campo | Tipo | Descripción |
|---|---|---|
| `owner` | string | Username autenticado. |
| `fileName` | string | Nombre aceptado del archivo. |
| `storedAt` | string | Ruta de guardado en el servidor; depende del directorio configurado y del sistema operativo (los separadores pueden variar). |
| `size` | integer | Tamaño guardado en bytes. |

Ejemplo completo usando el directorio default `./uploads` en un entorno POSIX y un archivo de 24 bytes:

```json
{
  "owner": "student",
  "fileName": "requirements.txt",
  "storedAt": "uploads/requirements.txt",
  "size": 24
}
```

5. **Errores:**

| Status | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| `400 Bad Request` | Nombre vacío, con separadores/ruta o NUL. | `{"detail":"Invalid file name"}` |
| `400 Bad Request` | Extensión distinta de `.txt`. | `{"detail":"Unsupported file extension"}` |
| `401 Unauthorized` | Header ausente o token inválido, malformado o vencido. | `{"detail":"Invalid token"}` |
| `413 Content Too Large` | El contenido supera 1 MiB. | `{"detail":"File is too large"}` |
| `422 Unprocessable Entity` | Falta el campo multipart requerido `file` o el request no puede validarse. | `{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input":null}]}` |
| `500 Internal Server Error` | Fallo inesperado de escritura/servidor. El formato interno no es un contrato estable; ejemplo del servidor ASGI por defecto: `Internal Server Error` (texto plano). | `Internal Server Error` |

6. **Notas de seguridad:** el propietario de la respuesta se deriva de la identidad, no de un campo enviado por el cliente. Solo se comprueban separadores de rutas POSIX/Windows, NUL y extensión; la validación actual acepta ciertos nombres con `:`, por ejemplo `requirements.txt:payload.txt` (H-API-03 pendiente), por lo que no debe considerarse una normalización completa. El servidor conserva el nombre validado y escribe hasta 1 MiB en el directorio configurado. Referencias: `api/app/routes.py:65-78`, `api/app/upload_service.py:7-38`, `api/app/security.py:11-20`.

### `GET /api/backend-health`

1. **Qué hace:** consulta el endpoint de salud del servicio de autenticación y devuelve su status y cuerpo al solicitante autenticado.

2. **Autenticación:** requerida. Header exacto: `Authorization: Bearer <token>`.

3. **Request:** no lleva query ni body. El destino es configuración del servidor: variable `AUTH_HEALTH_URL`; default `http://localhost:8080/q/health`.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `AUTH_HEALTH_URL` (entorno del servidor) | URL string | No | URL consultada por el backend; no es un parámetro que mande el cliente en esta ruta. |

Ejemplo completo:

```http
GET /api/backend-health HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token>
```

4. **Response exitosa:** `200 OK` para respuestas HTTP recibidas del upstream, incluso si el status upstream indica error; también es `200` si se captura un error de red o decodificación.

| Campo | Tipo | Descripción |
|---|---|---|
| `requestedBy` | string | Username autenticado que solicitó el chequeo. |
| `status` | integer | Status HTTP recibido del upstream; `0` si se captura un error HTTP de transporte/timeout o UTF-8 inválido. |
| `body` | string | Cuerpo upstream decodificado como UTF-8, o mensaje genérico si `status` es `0`. |

Ejemplo completo de upstream disponible:

```json
{
  "requestedBy": "student",
  "status": 200,
  "body": "{\"status\":\"UP\"}"
}
```

Ejemplo completo cuando el upstream no está disponible (también `200 OK`):

```json
{
  "requestedBy": "student",
  "status": 0,
  "body": "Backend health check unavailable"
}
```

5. **Errores:**

| Status | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token inválido, malformado o vencido. | `{"detail":"Invalid token"}` |
| `500 Internal Server Error` | Error inesperado no capturado, por ejemplo URL de upstream inválida/configuración problemática. Errores `HTTPError` y UTF-8 inválido se convierten en la respuesta `200` con `status: 0`; el formato de error interno no es contrato estable. | `Internal Server Error` (texto plano en el servidor ASGI por defecto) |

6. **Notas de seguridad:** solo el servidor elige el destino upstream mediante `AUTH_HEALTH_URL`, con timeout de 3 segundos. La ruta entrega el cuerpo upstream como texto; los errores de transporte y decodificación no filtran el detalle de la excepción. Revisar la URL de entorno al desplegar para evitar apuntar el chequeo a destinos no autorizados. Referencias: `api/app/routes.py:17-21,80-98`, `api/app/schemas.py:58-62`, `api/app/security.py:11-20`.

## Preguntas abiertas y riesgos

- **H-API-02:** ¿debe rechazarse con `403` un `owner` explícito vacío en query/body? El plan dice que sí para todo valor explícito no coincidente, pero el código usa `owner or username` y lo trata como omitido.
- **H-API-03:** ¿qué normalización y rechazo exactos de nombres se acordarán para caracteres especiales, incluido `:`? El nombre ADS `requirements.txt:payload.txt` pasa actualmente aunque se acordaron controles de nombre.
- **H-API-04:** falta acordar perfil JWT del emisor (algoritmo, `iss`, `aud`, claims y gestión de claves); hasta entonces estas rutas siguen aceptando el formato legacy Base64.
- El status y cuerpo ante excepciones internas no están definidos como contrato por estas rutas. Los ejemplos `500` reflejan el handler ASGI por defecto, no una respuesta JSON garantizada.

## Documentos consultados

- `README.md`
- `RETO.md`
- `docs/GOOD_PRACTICES.md`
- `HALLAZGOS.md`
- `PLAN.md`
- `api/app/main.py`
- `api/app/routes.py`
- `api/app/schemas.py`
- `api/app/security.py`
- `api/app/repositories.py`
- `api/app/services.py`
- `api/app/upload_service.py`
- `api/tests/test_api.py`