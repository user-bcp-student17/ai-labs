# Endpoints de ReqFlow

Documento compartido. Cada componente mantiene su propia sección; las secciones de `auth` y `web` las escriben sus componentes y no se tocan desde `api`.

## api

### Estado y alcance de este contrato

| Tipo | Contenido |
|---|---|
| **Contrato observado** | El descrito abajo; los endpoints se verificaron contra `api/app/` y con pruebas temporales. La actualización de H-API-04 se comprobó el 2026-11-02. No se ejecutó contra Docker Compose ni contra `auth`/`web`. |
| **Contrato acordado** | Solo las políticas de H-API-04 registradas en `PLAN.md`: extensiones, tamaño, colisiones, errores y referencia relativa. El resto de este documento no tiene aprobación humana registrada. |
| **Riesgos pendientes** | Ver [Riesgos pendientes y preguntas abiertas](#riesgos-pendientes-y-preguntas-abiertas), incluida la compatibilidad con los consumidores y H-API-11. |

Los hallazgos citados (H-API-NN) están en `HALLAZGOS.md`.

### Convenciones comunes

- **Base URL:** `http://localhost:8000` (puerto de la API según README.md). Documentación interactiva generada por FastAPI en `/docs`.
- **Formato:** JSON (`application/json`) salvo la subida de archivos (`multipart/form-data`) y los errores 500 (texto plano).
- **Rutas existentes:** solo `GET /api/tasks`, `POST /api/tasks`, `GET /api/summary`, `POST /api/requirements` y `GET /api/backend-health` (más `/docs`, `/openapi.json` y `/redoc` de FastAPI). Otro método sobre una ruta existente responde `405 {"detail":"Method Not Allowed"}`.
- **Todos los endpoints exigen autenticación** (ver siguiente sección).

#### Autenticación

Header exacto en todos los endpoints:

```
Authorization: Bearer <JWT>
```

El esquema `Bearer` no distingue mayúsculas (`bearer` también funciona). Verificación en `api/app/security.py:17-42` con la configuración de `api/app/config.py:24-52`:

| Regla | Valor |
|---|---|
| Algoritmo | Solo `HS256`. Otro algoritmo, incluido `none`, se rechaza. |
| Firma | Secreto compartido de la variable de entorno `WORKSHOP_JWT_SECRET` (obligatoria). |
| Claims obligatorios | `exp`, `iss`, `aud`, `sub`, `role`. Si falta cualquiera, o está vencido, se rechaza. |
| `iss` esperado | `WORKSHOP_JWT_ISSUER` (por defecto `reqflow-auth`). |
| `aud` esperado | `WORKSHOP_JWT_AUDIENCE` (por defecto `reqflow-api`). |
| Identidad | `sub` → nombre de usuario (`username`); `role` se exige pero **no se usa** para autorizar. |

Ejemplo de claims (JSON) de un token válido:

```json
{ "sub": "student", "role": "STUDENT", "exp": 1793570000, "iss": "reqflow-auth", "aud": "reqflow-api" }
```

Errores comunes de autenticación (aplican a los 5 endpoints):

| Código | Cuándo | Cuerpo |
|---|---|---|
| 401 | Falta el header, el esquema no es `Bearer`, el token está vacío, malformado, vencido, con firma/emisor/audiencia incorrectos o sin un claim obligatorio. El mensaje es siempre el mismo. | `{"detail":"Invalid token"}` |
| 500 | `WORKSHOP_JWT_SECRET` no está definida en el servidor y se envía un token (falla cerrado). | Texto plano: `Internal Server Error` |

La autenticación se evalúa antes que la validación ordinaria del cuerpo: una
petición sin token y con cuerpo inválido responde 401, no 422. En
`POST /api/requirements` el token se verifica antes de leer el cuerpo (H-API-12):
una solicitud sin credenciales válidas responde 401 aunque supere el límite de
tamaño y no se almacena. El 413 solo se devuelve a solicitudes autenticadas.

#### Errores de validación (422) y de método (405)

FastAPI devuelve este formato estándar en cualquier 422:

```json
{"detail":[{"type":"string_type","loc":["body","title"],"msg":"Input should be a valid string","input":["x"]}]}
```

`detail` es una lista; cada elemento trae `type`, `loc` (ruta del campo), `msg` e `input` (el valor recibido).

#### Configuración del servidor que afecta al contrato

| Variable | Defecto | Efecto |
|---|---|---|
| `WORKSHOP_JWT_SECRET` | (sin defecto) | Obligatoria para autenticar. |
| `WORKSHOP_JWT_ISSUER` | `reqflow-auth` | `iss` esperado. |
| `WORKSHOP_JWT_AUDIENCE` | `reqflow-api` | `aud` esperado. |
| `WORKSHOP_CORS_ORIGINS` | `http://localhost:4200` | Orígenes permitidos, separados por comas (`api/app/config.py:59-61`). |
| `WORKSHOP_DB_PATH` | `./data/workshop.db` | Base SQLite. |
| `WORKSHOP_UPLOAD_DIR` | `./uploads` | Carpeta de archivos subidos. |
| `AUTH_HEALTH_URL` | `http://localhost:8080/q/health` | URL que consulta `GET /api/backend-health`. |

**CORS** (`api/app/main.py:38-44`): solo los orígenes configurados reciben cabeceras CORS, con credenciales, métodos `GET`, `POST`, `OPTIONS` y cabeceras `Authorization` y `Content-Type`. Un origen no listado, o un método/cabecera no permitidos, falla el preflight con 400.

#### Modelo de tarea (se repite en varias respuestas)

Campos de una tarea, tal como se devuelven (`api/app/schemas.py:19-26`):

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | entero | Identificador autoincremental. |
| `title` | cadena | Título. |
| `description` | cadena | Descripción. |
| `status` | cadena | Estado, texto libre. Valores que usa el sistema: `TODO`, `IN_PROGRESS`, `DONE`, `ARCHIVED`. |
| `owner` | cadena | Usuario dueño; siempre es el del token. |
| `priority` | cadena | Prioridad, texto libre. Valores que usa el sistema: `HIGH`, `MEDIUM`, `LOW`. |
| `createdAt` | cadena | Fecha de creación, formato `YYYY-MM-DD HH:MM:SS` generado por SQLite (`datetime('now')`, UTC). |

Datos iniciales (base vacía): `id` 1 y 2 de `student` ("Refactor login", "Review API") e `id` 3 de `trainer` ("Trainer notes") (`api/app/repository.py:14-18`). La primera tarea creada recibe `id` 4.

---

### GET /api/tasks

**1. Qué hace.** Lista las tareas del usuario autenticado, ordenadas por `id` (`api/app/routes/tasks.py:12-18`).

**2. Autenticación.** Sí: `Authorization: Bearer <JWT>`.

**3. Request.**

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `owner` (query) | cadena | No | Solo se acepta el propio usuario del token. Omitirlo equivale a usar el propio usuario. Cualquier otro valor, **incluida la cadena vacía**, da 403. |

Ejemplo:

```http
GET /api/tasks HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**4. Respuesta exitosa: 200.** Arreglo JSON de tareas con los campos del [modelo de tarea](#modelo-de-tarea-se-repite-en-varias-respuestas). Arreglo vacío si el usuario no tiene tareas.

```json
[
  {"id":1,"title":"Refactor login","description":"Separar responsabilidades en frontend","status":"TODO","owner":"student","priority":"HIGH","createdAt":"2026-11-02 21:59:43"},
  {"id":2,"title":"Review API","description":"Revisar seguridad de endpoints","status":"IN_PROGRESS","owner":"student","priority":"MEDIUM","createdAt":"2026-11-02 21:59:43"}
]
```

**5. Errores.**

| Código | Cuándo | Cuerpo |
|---|---|---|
| 401 | Token ausente o inválido (ver Autenticación). | `{"detail":"Invalid token"}` |
| 403 | `owner` distinto del usuario del token (o vacío). | `{"detail":"Access to another owner is forbidden"}` |
| 500 | Secreto JWT no configurado en el servidor. | `Internal Server Error` (texto plano) |

**6. Seguridad.** La autorización depende de la identidad del token (`sub`), no de `owner`: el parámetro se conserva por compatibilidad, pero ya no permite leer tareas ajenas (H-API-02, `api/app/security.py:45-48`). El filtro por dueño usa una consulta parametrizada (H-API-03, `api/app/repository.py:10`). El rol del token no concede acceso a otros usuarios.

---

### POST /api/tasks

**1. Qué hace.** Crea una tarea a nombre del usuario autenticado (`api/app/routes/tasks.py:21-27`).

**2. Autenticación.** Sí: `Authorization: Bearer <JWT>`.

**3. Request.** Cuerpo JSON (`Content-Type: application/json`). Ningún campo es obligatorio. Los campos desconocidos se ignoran.

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `title` | cadena | No (defecto `""`) | Título. Acepta vacío; no admite `null` ni otro tipo. |
| `description` | cadena | No (defecto `""`) | Descripción. |
| `status` | cadena | No (defecto `"TODO"`) | Estado. Texto libre, sin lista cerrada (ver preguntas abiertas). |
| `priority` | cadena | No (defecto `"MEDIUM"`) | Prioridad. Texto libre. |
| `owner` | cadena o `null` | No | Solo se acepta el propio usuario del token (o ausente/`null`). Otro valor, incluida la cadena vacía, da 403. |

Ejemplo:

```http
POST /api/tasks HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{"title":"Write docs","description":"Document the API","status":"IN_PROGRESS","priority":"HIGH"}
```

**4. Respuesta exitosa: 201.** La tarea creada, con los campos del [modelo de tarea](#modelo-de-tarea-se-repite-en-varias-respuestas).

```json
{"id":4,"title":"Write docs","description":"Document the API","status":"IN_PROGRESS","owner":"student","priority":"HIGH","createdAt":"2026-11-02 21:59:43"}
```

Con cuerpo `{}` se crea con los valores por defecto: `{"id":5,"title":"","description":"","status":"TODO","owner":"student","priority":"MEDIUM","createdAt":"2026-11-02 21:59:43"}`.

**5. Errores.**

| Código | Cuándo | Cuerpo |
|---|---|---|
| 401 | Token ausente o inválido. | `{"detail":"Invalid token"}` |
| 403 | `owner` distinto del usuario del token. | `{"detail":"Access to another owner is forbidden"}` |
| 422 | Sin cuerpo: `{"detail":[{"type":"missing","loc":["body"],"msg":"Field required","input":null}]}`. Un campo de texto con otro tipo o `null`: `{"detail":[{"type":"string_type","loc":["body","title"],"msg":"Input should be a valid string","input":["x"]}]}`. JSON mal formado o cuerpo que no es JSON/objeto: mismo formato 422 con `type` `json_invalid` o `model_attributes_type`. | ver columna |
| 500 | Secreto JWT no configurado en el servidor. | `Internal Server Error` (texto plano) |

**6. Seguridad.** El dueño de la tarea es siempre el del token: nadie puede crear tareas a nombre de otro (H-API-02). El `INSERT` está parametrizado: comillas y metacaracteres SQL se guardan como texto literal (H-API-03, `api/app/repository.py:13`). No hay validación de valores de `status`/`priority` ni longitud máxima de textos.

---

### GET /api/summary

**1. Qué hace.** Devuelve el conteo de tareas del usuario autenticado, por estado y cuántas de prioridad alta siguen abiertas (`api/app/routes/tasks.py:30-36`).

**2. Autenticación.** Sí: `Authorization: Bearer <JWT>`.

**3. Request.**

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `owner` (query) | cadena | No | Igual que en `GET /api/tasks`: solo el propio usuario; otro valor o vacío → 403. |

Ejemplo:

```http
GET /api/summary HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**4. Respuesta exitosa: 200** (`api/app/schemas.py:29-33`).

| Campo | Tipo | Descripción |
|---|---|---|
| `owner` | cadena | Usuario del token. |
| `total` | entero | Número de tareas del usuario. |
| `byStatus` | objeto (cadena → entero) | Conteo por valor de `status`; solo aparecen los estados que existen. `{}` si no hay tareas. |
| `highPriorityOpen` | entero | Tareas con `priority` igual a `HIGH` y `status` distinto de `DONE` y `ARCHIVED`. |

Con los datos iniciales de `student`:

```json
{"owner":"student","total":2,"byStatus":{"TODO":1,"IN_PROGRESS":1},"highPriorityOpen":1}
```

Usuario sin tareas: `{"owner":"nobody","total":0,"byStatus":{},"highPriorityOpen":0}`.

**5. Errores.**

| Código | Cuándo | Cuerpo |
|---|---|---|
| 401 | Token ausente o inválido. | `{"detail":"Invalid token"}` |
| 403 | `owner` distinto del usuario del token (o vacío). | `{"detail":"Access to another owner is forbidden"}` |
| 500 | Secreto JWT no configurado en el servidor. | `Internal Server Error` (texto plano) |

**6. Seguridad.** Igual que `GET /api/tasks`: el resumen es siempre del usuario del token y la consulta está parametrizada (H-API-02, H-API-03, `api/app/repository.py:12`).

---

### POST /api/requirements

**1. Qué hace.** Recibe un archivo de requerimientos y lo guarda en el servidor, a nombre del usuario autenticado (`api/app/routes/requirements.py:11-18`).

**2. Autenticación.** Sí: `Authorization: Bearer <JWT>`.

**3. Request.** `multipart/form-data` con un campo de archivo.

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `file` | archivo | Sí | Hasta 5 MiB. Extensiones `.txt`, `.md`, `.pdf` y `.docx`, sin distinguir mayúsculas. |

Ejemplo:

```http
POST /api/requirements HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: multipart/form-data; boundary=----b

------b
Content-Disposition: form-data; name="file"; filename="requirements.txt"
Content-Type: text/plain

Login must be accessible
------b--
```

**4. Respuesta exitosa: 201** (`api/app/schemas.py:36-40`).

| Campo | Tipo | Descripción |
|---|---|---|
| `owner` | cadena | Usuario del token. |
| `fileName` | cadena | Nombre validado y normalizado a Unicode NFC. |
| `storedAt` | cadena | Referencia relativa: el nombre validado del archivo, sin ruta interna. |
| `size` | entero | Bytes guardados. |

```json
{"owner":"student","fileName":"requirements.txt","storedAt":"requirements.txt","size":24}
```

**5. Errores.**

| Código | Cuándo | Cuerpo |
|---|---|---|
| 400 | Nombre inválido, por ejemplo con separadores, ruta absoluta o caracteres de control. | `{"detail":"Invalid filename"}` |
| 401 | Token ausente o inválido. Se responde antes de leer el cuerpo, también si este supera el límite. | `{"detail":"Invalid token"}` |
| 409 | Ya existe un archivo con ese nombre, incluso si lo subió otro usuario. | `{"detail":"File already exists"}` |
| 413 | Solo con token válido: archivo mayor de 5 MiB o solicitud mayor de 5 MiB más 64 KiB de margen multipart. | `{"detail":"File too large"}` o `{"detail":"Request too large"}` |
| 415 | Extensión no permitida o ausente. | `{"detail":"File extension not allowed"}` |
| 422 | Falta el campo `file`: `{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input":null}]}`. También si la parte no trae nombre de archivo (observado con `filename=""`). | ver columna |
| 500 | Secreto JWT no configurado o fallo inesperado de lectura o escritura. | `Internal Server Error` (texto plano) |

**6. Seguridad.** El nombre se valida antes de escribir; no se siguen enlaces
existentes en el destino y la publicación no sobrescribe archivos.
Se limita el cuerpo antes del procesamiento multipart y el archivo se lee por
bloques (`api/app/upload_limit.py:11`, `api/app/uploads.py:38`). El `owner`
de respuesta proviene del token. Las colisiones se comprueban en el directorio
compartido, no hay directorios separados por usuario. La dependencia transitiva
`starlette` mantiene advisories pendientes (H-API-11).

---

### GET /api/backend-health

**1. Qué hace.** Consulta el estado del servicio de autenticación (`auth`) desde la API y lo devuelve junto con quién lo pidió (`api/app/routes/health.py:11-12`).

**2. Autenticación.** Sí: `Authorization: Bearer <JWT>`.

**3. Request.** Sin parámetros ni cuerpo. El servidor consulta la URL de `AUTH_HEALTH_URL` (por defecto `http://localhost:8080/q/health`, `http://auth:8080/q/health` en compose) con `GET` y timeout de 3 s.

```http
GET /api/backend-health HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**4. Respuesta exitosa: 200** (`api/app/schemas.py:43-46`). Responde 200 tanto si `auth` contestó como si no; mira `status` para saber el resultado.

| Campo | Tipo | Descripción |
|---|---|---|
| `requestedBy` | cadena | Usuario del token. |
| `status` | entero | Código HTTP que devolvió `auth` (el que sea, incluso 4xx/5xx), o `0` si no se pudo conectar. |
| `body` | cadena | Cuerpo que devolvió `auth` (decodificado como UTF-8), o el texto fijo `Backend unavailable` si `status` es `0`. |

`auth` disponible (el `body` es el texto que envíe `auth`; aquí, un ejemplo de servidor de prueba):

```json
{"requestedBy":"student","status":200,"body":"{\"status\":\"UP\",\"checks\":[]}"}
```

`auth` no disponible (conexión rechazada, timeout o error de red):

```json
{"requestedBy":"student","status":0,"body":"Backend unavailable"}
```

**5. Errores.**

| Código | Cuándo | Cuerpo |
|---|---|---|
| 401 | Token ausente o inválido. | `{"detail":"Invalid token"}` |
| 500 | Secreto JWT no configurado en el servidor. | `Internal Server Error` (texto plano) |

Un fallo de red hacia `auth` **no** es un error HTTP: devuelve 200 con `status` 0.

**6. Seguridad.** Exige token válido. El detalle del fallo de conexión (host, puerto, excepción) no se devuelve al cliente: solo va al log del servidor (H-API-06, `api/app/services.py:45-50`). La URL consultada la fija el servidor (`AUTH_HEALTH_URL`); el cliente no puede cambiarla. El `body` reenvía tal cual lo que responda `auth`, sin límite de tamaño.

---

### Riesgos pendientes y preguntas abiertas

| # | Tema | Detalle |
|---|---|---|
| 1 | Emisión del token | `api` solo acepta JWT HS256 con `iss`/`aud`/secreto configurados. No está acordado con `auth` (qué emite, con qué `iss`, `aud`, secreto y claims `sub`/`role`). Los valores `reqflow-auth`/`reqflow-api` son provisionales. Pregunta abierta para `auth`. |
| 2 | Compose | `compose.yaml` no define `WORKSHOP_JWT_SECRET` para `api`; con un token presente, toda petición respondería 500 hasta definirlo. No se probó con Compose. |
| 3 | Subida de archivos | H-API-04 corregido según la decisión registrada; queda por verificar con los consumidores la referencia relativa y los nuevos errores. |
| 4 | Valores de `status`/`priority` | Son texto libre. Pregunta abierta: ¿lista cerrada (y 422 para otros valores)? |
| 5 | `owner` | Se conserva por compatibilidad, pero solo admite al propio usuario. Pregunta abierta: ¿`web` lo envía? ¿debe el rol `TRAINER` poder ver a otros? No se asume. |
| 6 | Cambio de contrato respecto al comportamiento original | 401 genérico y 403 nuevo; `Bearer` obligatorio; `owner` vacío ahora da 403; textos no-cadena dan 422. Pendiente confirmar con `web`. |
| 7 | Dependencias | `starlette 0.50.0` con advisories (H-API-11). |
| 8 | Mensaje de 500 | Los 500 son texto plano `Internal Server Error`, no JSON. Observado, no diseñado. |
| 9 | Almacenamiento | La publicación usa enlaces duros en el directorio configurado; requiere un sistema de archivos que los admita. No se ha verificado el despliegue con Compose. |

### Referencias de verificación

`api/app/routes/tasks.py`, `api/app/routes/requirements.py`, `api/app/routes/health.py`, `api/app/security.py`, `api/app/config.py`, `api/app/schemas.py`, `api/app/services.py`, `api/app/repository.py`, `api/app/main.py` y las pruebas `api/tests/`.
