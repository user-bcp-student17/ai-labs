# Pruebas de ReqFlow

Documento compartido. Cada componente mantiene su propia sección; las de `auth` y `web` no se tocan desde `api`.

## api

Pruebas de la API FastAPI contra el contrato de la sección `api` de [ENDPOINTS.md](./ENDPOINTS.md). Cada ejecución se relaciona con el componente `api` y los IDs de `HALLAZGOS.md` (H-API-NN).

### Actualización H-API-04 — 2026-11-02

La sección siguiente conserva la evidencia histórica previa a la corrección:
sus expectativas de archivo sin extensión, sobrescritura, ruta absoluta y
`xfail` ya no representan el comportamiento actual. La nueva política fue
aprobada por el usuario y está documentada en `PLAN.md` y `ENDPOINTS.md`.

| Componente e ID | Momento | Comando con cwd `api/` | Salida | Resultado real |
|---|---|---|---|---|
| api, H-API-04 | Caracterización anterior | `.\.venv\Scripts\python.exe -m pytest tests\test_endpoints_contract.py -k "post_requirements" -rx` | 0 | 10 passed, 1 xfailed, 54 deselected |
| api, H-API-04 | Corrección antes | `.\.venv\Scripts\python.exe -m pytest tests\test_upload_security.py -q --tb=no` | 1 | 21 failed, 3 passed; las pruebas se escribieron antes del cambio |
| api, H-API-04 | Caracterización y corrección después | `.\.venv\Scripts\python.exe -m pytest -o addopts='' tests\test_upload_security.py tests\test_endpoints_contract.py -k "post_requirements or upload_security" -q` | 0 | 38 passed, 54 deselected, 1 warning |
| api, H-API-04 y regresión | Suite completa | `.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=json:coverage.json --cov-fail-under=85` | 0 | 162 passed, 1 warning; cobertura global combinada 98.22% |

Las pruebas focalizadas incluyen extensión y nombre, traversal, enlace
simbólico, tamaño exacto y excedido, límite multipart sin `Content-Length`,
interrupción de lectura y escritura, colisiones y concurrencia. El `xfail`
de traversal se retiró después de que pasara; las caracterizaciones que
describían el contrato anterior se actualizaron por la decisión aprobada.

Cobertura del diff de `api/app` frente a `main`: **290/293 sentencias
ejecutables modificadas (98.98%)**, intersección de las líneas añadidas por
`git diff main -U0 -- api/app` y de todos los archivos Python nuevos sin
seguimiento con el JSON de `coverage.py`. Cobertura global: **302/305
sentencias y 29/32 ramas**, combinada 98.22%; reporte HTML en
`api/htmlcov/index.html`. El archivo JSON temporal se retiró tras calcular
la cobertura. No se ejecutó integración con `auth`, `web` ni Compose.

### Resumen

| Concepto | Valor |
|---|---|
| Archivo nuevo de este paso | `api/tests/test_endpoints_contract.py` (65 pruebas: 64 pasan, 1 `xfail` por H-API-04) |
| Suite completa | 135 pruebas: **134 pasaron, 1 xfailed (esperado), 0 fallaron** |
| Código de producción | No se modificó en este paso |
| Entorno | Windows, Python 3.14.7, `api/.venv` (FastAPI 0.128.2, pytest 9.0.2, pytest-cov 7.0.0) |
| Sin ejecutar | Python 3.13 (versión de README/Dockerfile) con las pruebas nuevas; Docker Compose; integración con `auth`/`web` |

### Cómo ejecutarlas y qué resultó

Resultados reales de esta sesión (2026-11-02).

| # | IDs | Directorio | Comando | Código de salida | Resultado |
|---|---|---|---|---|---|
| 1 | todos los endpoints; H-API-04 (xfail) | `api/` | `.\.venv\Scripts\python.exe -m pytest tests/test_endpoints_contract.py -p no:warnings -rxXf` | 0 | 64 passed, 1 xfailed en 20.15 s |
| 2 | todos los endpoints; H-API-01 a H-API-10 | raíz | `python tools/lab.py test api` (ejecuta `pytest --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=85` en `api/`) | 0 | 134 passed, 1 xfailed, 1 warning (de `starlette.testclient`, `anyio.abc.BlockingPortal` en desuso; ajena a `api/app`) en 38.63 s. Gate de 85 % cumplido |
| 3 | cobertura | `api/` | `.\.venv\Scripts\python.exe -m pytest --cov=app --cov-branch --cov-report=json:<temp>` + script de líneas modificadas | 0 | Ver "Cobertura" |

Reporte HTML de la corrida #2: `api/htmlcov/index.html` (ignorado por Git).

### Cobertura

| Medida | Numerador / denominador | % | Método |
|---|---|---|---|
| **Código modificado** (líneas ejecutables) | **219 / 219** | **100 %** | Se tomaron las líneas ejecutables de `coverage.py` (ejecutadas + no ejecutadas, `--cov=app --cov-branch`, JSON) que están en el diff `git diff main -U0 -- api/app` (para `main.py`) o en archivos nuevos sin seguimiento (todas sus líneas: `config.py`, `dependencies.py`, `repository.py`, `schemas.py`, `security.py`, `services.py`, `routes/`). Ninguna línea modificada queda sin cubrir. Meta: 85 %. |
| **Global** `api/app` (líneas) | 231 / 231 | 100 % | Mismo reporte, todo `app`. Son 12 sentencias más que las modificadas: líneas sin cambios de `main.py`, como los `import`. |
| **Global** `api/app` (ramas) | 12 / 12 | 100 % | Mismo reporte (`--cov-branch`). |
| **Global** combinado (gate de `lab.py`) | 231 sentencias, 0 sin cubrir, 12 ramas, 0 parciales | 100 % | `python tools/lab.py test api`, umbral `--cov-fail-under=85`; no se cambió ningún umbral. |

Aviso honesto: la cobertura ya era del 100 % antes de este paso (70 pruebas). Las 65 nuevas no la suben; aportan **verificación del contrato** (valores, cuerpos y códigos), no líneas nuevas. La cobertura de líneas no demuestra que cada respuesta sea correcta.

### Tabla de casos por endpoint

Tipo: **Feliz** = dato válido; **Borde** = límite o entrada inusual; **Error** = respuesta de error documentada en ENDPOINTS.md. La columna "Archivo" indica dónde está la prueba si no es `test_endpoints_contract.py` (`EC`).

#### GET /api/tasks

| Caso | Tipo | Resultado esperado | Prueba |
|---|---|---|---|
| Trainer lista sus tareas | Feliz | 200, solo `Trainer notes`, `createdAt` con formato `YYYY-MM-DD HH:MM:SS` | EC `test_get_tasks_happy_path_trainer_sees_only_own_task` |
| Student lista sus tareas iniciales | Feliz | 200, `id` 1 y 2, claves exactas del modelo | `test_characterization.py::test_lists_seeded_tasks_with_exact_shape` |
| Usuario sin tareas | Borde | 200, `[]` | EC `..._user_without_tasks_gets_empty_list` |
| Esquema `bearer` en minúsculas | Borde | 200 | EC `..._bearer_scheme_is_case_insensitive` |
| Tareas creadas salen tras las iniciales, por `id` | Borde | ids `[1, 2, 4, 5]` | EC `..._created_tasks_are_listed_after_seed_in_id_order` |
| Tarea creada por un usuario no la ve otro | Borde | trainer solo ve `Trainer notes` | EC `..._invisible_to_another` |
| `owner` igual al propio usuario | Borde | igual que sin `owner` | `test_characterization.py::test_explicit_own_owner_matches_default` |
| Sin header `Authorization` | Error 401 | `{"detail":"Invalid token"}` | EC `..._error_401_without_authorization_header`; token malo/vencido/otro secreto/legado: `test_token_verification.py` |
| **Usuario no puede leer tareas de otro `owner`** | Error 403 | `{"detail":"Access to another owner is forbidden"}`, sin datos de trainer | EC `..._error_403_user_cannot_read_tasks_of_another_owner`; también `test_authorization.py::test_h_api_02_*` |
| `owner` vacío | Error 403 | mismo cuerpo 403 | EC `..._error_403_empty_owner_is_forbidden` |
| Secreto JWT no configurado | Error 500 | texto plano `Internal Server Error` | EC `test_every_endpoint_error_500_...` (parametrizada ×5) |

#### POST /api/tasks

| Caso | Tipo | Resultado esperado | Prueba |
|---|---|---|---|
| Payload completo | Feliz | 201, objeto con `id` 4, `owner` `student`, campos enviados; aparece en `GET /api/tasks` | EC `test_post_tasks_happy_path_creates_and_persists_task` |
| Objeto vacío `{}` | Borde | 201 con `title ""`, `description ""`, `status TODO`, `priority MEDIUM` | EC `..._edge_empty_object_uses_defaults` |
| Solo `title` | Borde | 201 con valores por defecto | `test_characterization.py::test_create_task_applies_defaults` |
| Campos desconocidos | Borde | 201, el campo no aparece en la respuesta | EC `..._edge_unknown_fields_are_ignored` |
| `owner: null` | Borde | 201, `owner` = usuario del token | EC `..._edge_null_owner_means_own_user` |
| Unicode y texto largo (5 000+ caracteres) | Borde | 201 y se guarda íntegro | EC `..._edge_unicode_and_long_text_are_stored_intact` |
| Comillas y metacaracteres SQL | Borde | se guardan como texto literal | `test_sql_parameterization.py` (H-API-03) |
| Sin token, con cuerpo inválido | Error 401 | 401 (la autenticación va antes que la validación) | EC `..._error_401_without_token_even_with_invalid_body` |
| `owner` ajeno | Error 403 | cuerpo 403 y no se crea la tarea de trainer | EC `..._error_403_creating_for_another_owner` |
| `owner` vacío | Error 403 | cuerpo 403 | EC `..._error_403_empty_owner_is_forbidden` |
| Campo con tipo erróneo (6 variantes: `title` lista/`null`, `description` número, `status` `null`, `priority` objeto, `owner` número) | Error 422 | `detail[0].type` `string_type` y `loc` del campo | EC `..._error_422_field_with_wrong_type` (parametrizada ×6) |
| Sin cuerpo | Error 422 | `type` `missing`, `loc` `["body"]` | EC `..._error_422_without_body` |
| JSON mal formado | Error 422 | `type` `json_invalid` | EC `..._error_422_malformed_json` |
| Cuerpo de formulario en vez de JSON | Error 422 | `type` `model_attributes_type` | EC `..._error_422_form_body_instead_of_json` |
| 422 no crea tarea | Error 422 | GET sigue con 2 tareas | EC `test_post_tasks_422_does_not_create_a_task` |
| Secreto JWT no configurado | Error 500 | `Internal Server Error` | EC `test_every_endpoint_error_500_...` |

#### GET /api/summary

| Caso | Tipo | Resultado esperado | Prueba |
|---|---|---|---|
| Resumen de datos iniciales | Feliz | `{"owner":"student","total":2,"byStatus":{"TODO":1,"IN_PROGRESS":1},"highPriorityOpen":1}` | `test_characterization.py::test_summary_of_seeded_data` |
| Tras crear tareas | Feliz | `total` 4, `byStatus` `{TODO:2, IN_PROGRESS:1, DONE:1}`, `highPriorityOpen` 2 | EC `test_get_summary_happy_path_after_creating_tasks` |
| HIGH con DONE/ARCHIVED no cuentan | Borde | `highPriorityOpen` solo las abiertas | `test_characterization.py::test_summary_counts_only_open_high_priority` |
| Usuario sin tareas | Borde | `total` 0, `byStatus` `{}`, `highPriorityOpen` 0 | EC `..._edge_user_without_tasks` |
| Tareas de otros usuarios no se cuentan | Borde | student 2, trainer 2 (1 inicial + 1 creada) | EC `..._edge_other_users_tasks_are_not_counted` |
| `status` libre y `priority` en minúscula | Borde | `status` cuenta en `byStatus`; `high` no suma a `highPriorityOpen` | EC `..._free_text_status_is_counted_and_priority_is_case_sensitive` |
| Sin token | Error 401 | `{"detail":"Invalid token"}` | EC `..._error_401_without_token` |
| **Resumen de otro `owner`** | Error 403 | cuerpo 403 | EC `..._error_403_user_cannot_read_summary_of_another_owner` |
| `owner` vacío | Error 403 | cuerpo 403 | EC `..._error_403_empty_owner_is_forbidden` |
| Secreto JWT no configurado | Error 500 | `Internal Server Error` | EC `test_every_endpoint_error_500_...` |

#### POST /api/requirements

| Caso | Tipo | Resultado esperado | Prueba |
|---|---|---|---|
| Subir `requirements.txt` | Feliz | 201, `{"owner":"student","fileName":"requirements.txt","storedAt":<carpeta>/requirements.txt,"size":24}` y contenido guardado idéntico | EC `test_post_requirements_happy_path_stores_file_and_returns_contract` |
| Archivo sin extensión | Borde | 201, se guarda como `README` | EC `..._edge_file_without_extension_is_accepted` |
| Archivo vacío | Borde | 201, `size` 0 | EC `..._edge_empty_file_has_size_zero` |
| Archivo de 1 MiB binario (tamaño límite probado: ENDPOINTS.md documenta que no hay tope) | Borde | 201, `size` 1 048 576, bytes idénticos | EC `..._edge_binary_content_is_stored_byte_for_byte` |
| Mismo nombre dos veces | Borde | el segundo contenido reemplaza al primero | EC `..._edge_file_with_same_name_is_overwritten` |
| Nombre con espacios | Borde | 201, se guarda con el mismo nombre | EC `..._edge_filename_with_spaces` |
| Sin token (con archivo) | Error 401 | cuerpo 401 y no se escribe archivo | EC `..._error_401_without_token` |
| Token inválido | Error 401 | cuerpo 401 | EC `..._error_401_with_invalid_token` |
| Falta el campo `file` | Error 422 | `type` `missing`, `loc` `["body","file"]` | EC `..._error_422_without_file_field` |
| Parte sin nombre de archivo | Error 422 | `loc` `["body","file"]` | EC `..._error_422_part_without_filename` |
| Secreto JWT no configurado | Error 500 | `Internal Server Error` | EC `test_every_endpoint_error_500_...` |
| **Nombre con `../`** | Seguridad (H-API-04) | El archivo debe quedar dentro de la carpeta de subida | EC `..._security_traversal_name_stays_inside_upload_dir`: **`xfail` estricto, hoy falla** (ver "Fallos") |

#### GET /api/backend-health

| Caso | Tipo | Resultado esperado | Prueba |
|---|---|---|---|
| `auth` responde 200 con JSON | Feliz | 200, `{"requestedBy":"trainer","status":200,"body":"{\"status\":\"UP\",\"checks\":[]}"}` | EC `test_get_backend_health_happy_path_relays_upstream_json` |
| `auth` responde 503 | Borde | HTTP 200, `status` 503, `body` `DOWN` | EC `..._edge_upstream_error_status_is_relayed_with_http_200` |
| Cuerpo vacío (204) | Borde | `status` 204, `body` `""` | EC `..._edge_empty_upstream_body` |
| Cuerpo no UTF-8 | Borde | HTTP 200, bytes inválidos reemplazados por U+FFFD | EC `..._edge_non_utf8_body_is_decoded_with_replacement` |
| `auth` no disponible | Borde | HTTP 200, `status` 0, `body` `Backend unavailable` | EC `..._edge_unreachable_backend_returns_http_200_status_zero` |
| El cliente intenta fijar la URL (`?url=`) | Borde | se ignora; usa `AUTH_HEALTH_URL` | EC `..._client_cannot_choose_the_url` |
| Sin token | Error 401 | cuerpo 401 | EC `..._error_401_without_token` |
| Secreto JWT no configurado | Error 500 | `Internal Server Error` | EC `test_every_endpoint_error_500_...` |

#### Todos los endpoints

| Caso | Tipo | Resultado esperado | Prueba |
|---|---|---|---|
| Token basura, vencido o esquema `Basic` | Error 401 | `{"detail":"Invalid token"}` | EC `test_every_endpoint_error_401_body_is_generic_for_invalid_tokens` (×5) |
| Sin token | Error 401 | 401 | `test_characterization.py::test_every_endpoint_requires_a_token` (×5) |
| Método no ofrecido (`DELETE /api/tasks`, `PUT /api/summary`, `GET /api/requirements`, `POST /api/backend-health`) | Error 405 | `{"detail":"Method Not Allowed"}` | EC `test_error_405_for_methods_not_offered` (×4) |
| CORS | Borde/Error | Origen no listado sin cabeceras, preflight 400 | `test_cors.py` (H-API-07) |

### Fallos, bugs y pendientes (separados)

**Fallos de la suite:** ninguno (0 failed).

**Bug conocido, reportado aparte y no escondido: H-API-04 (alta, "Pendiente").**
- La prueba `test_post_requirements_security_traversal_name_stays_inside_upload_dir` describe el comportamiento **correcto** (el archivo `../escape.txt` no puede salir de la carpeta de subida). Hoy el código lo escribe fuera ([api/app/services.py:39-41](../api/app/services.py)), por lo que está marcada `xfail(strict=True)`. El `xfail` estricto impide ocultarlo: cuando H-API-04 se corrija, la prueba pasará, la suite fallará por `XPASS` y obligará a quitar el marcador. No se adaptó ninguna aserción para que "pase" con el bug.
- Mismo origen, **no probado como prueba verde**: no hay tope de tamaño (solo se probó 1 MiB), cualquier extensión se acepta y el nombre se usa tal cual.

**Pruebas que fijan decisiones pendientes de H-API-04** (documentadas en ENDPOINTS.md como comportamiento actual; revisar cuando se decida la política): `..._file_without_extension_is_accepted`, `..._file_with_same_name_is_overwritten`, `..._binary_content_is_stored_byte_for_byte` (1 MiB aceptado). Si H-API-04 rechaza extensiones, impone tope o evita sobrescribir, deben cambiarse a propósito, no para "arreglar" un rojo.

**Comportamientos raros observados, sin prueba (no son contrato):**
- Un nombre de archivo de 300 caracteres produjo 500 en Windows; puede variar según el sistema operativo.
- Una parte multipart con `filename=""` da 422 con mensaje de FastAPI poco claro (`Expected UploadFile, received: <class 'str'>`); se probó solo el código 422 y `loc`.

**Pendientes (no ejecutados):**
- Pruebas nuevas en Python 3.13 (la suite anterior, 70 pruebas, sí pasó en 3.13 en la revisión previa); Docker Compose; integración `auth` → `api` → `web`.
- Aprobación humana de este documento y de las pruebas: no hay ninguna registrada.
- H-API-10 sigue "Pendiente" (`app = create_app()` con efectos al importar): sin prueba que lo cubra.
- H-API-11 (starlette con advisories): `pip-audit` no se incluyó en la suite.

### Pruebas propuestas (no implementadas)

Para cuando se decida H-API-04 y se acuerde con `auth`:

1. Rechazo de nombre con separadores (`..`, `/`, `\`, ruta absoluta) y normalización del nombre.
2. Lista blanca de extensiones: `.exe` rechazada, archivo sin extensión según política.
3. Tope de tamaño: archivo mayor que el límite rechazado antes de leerse completo (y 1 byte bajo el límite aceptado).
4. Nombre repetido (según política: no sobrescribir o nombre único) y aislamiento entre usuarios.
5. `storedAt` sin ruta absoluta del servidor, si se acuerda.
6. Nombre de 300 caracteres devuelve error controlado, no 500.
7. Lista cerrada de `status`/`priority` con 422 (si se acuerda).
8. Token emitido realmente por `auth` aceptado por `api` (prueba de integración con `iss`, `aud`, secreto y claims acordados).
9. `pip-audit -r api/requirements.txt` (resolviendo dependencias) en CI o como prueba, y comprobación de `starlette`.
10. Importar `app.main` no crea carpetas ni abre la base (H-API-10).

### Código de las pruebas nuevas

Archivo: `api/tests/test_endpoints_contract.py`. Usa las fixtures `client` y `jwt_environment` de `api/tests/conftest.py`, los tokens de `api/tests/tokens.py` y el servidor de salud de `api/tests/test_characterization.py`. Ninguna prueba toca archivos fuera de `tmp_path`.

```python
"""Pruebas por endpoint según docs/ENDPOINTS.md (sección api): camino feliz, casos borde y errores."""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_characterization import health_server
from tests.tokens import auth, bearer, make_token

CREATED_AT_FORMAT = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
FIRST_CREATED_TASK_ID = 4
INVALID_TOKEN = {"detail": "Invalid token"}
FORBIDDEN_OWNER = {"detail": "Access to another owner is forbidden"}
TEXT_FILE = ("requirements.txt", b"Login must be accessible", "text/plain")

ENDPOINTS = [
    ("get", "/api/tasks"),
    ("post", "/api/tasks"),
    ("get", "/api/summary"),
    ("post", "/api/requirements"),
    ("get", "/api/backend-health"),
]


def _upload(client: TestClient, file: tuple[str, bytes, str], headers: dict[str, str] | None = None):
    return client.post("/api/requirements", headers=headers or auth(), files={"file": file})


def _without_created_at(task: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in task.items() if key != "createdAt"}


# ---------------------------------------------------------------- GET /api/tasks


def test_get_tasks_happy_path_trainer_sees_only_own_task(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=auth("trainer"))
    assert response.status_code == 200
    assert [_without_created_at(task) for task in response.json()] == [
        {"id": 3, "title": "Trainer notes", "description": "Preparar retrospectiva", "status": "TODO", "owner": "trainer", "priority": "LOW"}
    ]
    assert CREATED_AT_FORMAT.match(response.json()[0]["createdAt"])


def test_get_tasks_edge_user_without_tasks_gets_empty_list(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=auth("nobody"))
    assert (response.status_code, response.json()) == (200, [])


def test_get_tasks_edge_bearer_scheme_is_case_insensitive(client: TestClient) -> None:
    headers = {"Authorization": "bearer " + make_token()}
    assert client.get("/api/tasks", headers=headers).status_code == 200


def test_get_tasks_edge_created_tasks_are_listed_after_seed_in_id_order(client: TestClient) -> None:
    client.post("/api/tasks", headers=auth(), json={"title": "first"})
    client.post("/api/tasks", headers=auth(), json={"title": "second"})
    ids = [task["id"] for task in client.get("/api/tasks", headers=auth()).json()]
    assert ids == [1, 2, 4, 5]


def test_get_tasks_edge_tasks_created_by_one_user_are_invisible_to_another(client: TestClient) -> None:
    client.post("/api/tasks", headers=auth(), json={"title": "private"})
    titles = [task["title"] for task in client.get("/api/tasks", headers=auth("trainer")).json()]
    assert titles == ["Trainer notes"]


def test_get_tasks_error_401_without_authorization_header(client: TestClient) -> None:
    response = client.get("/api/tasks")
    assert (response.status_code, response.json()) == (401, INVALID_TOKEN)


def test_get_tasks_error_403_user_cannot_read_tasks_of_another_owner(client: TestClient) -> None:
    response = client.get("/api/tasks", params={"owner": "trainer"}, headers=auth())
    assert (response.status_code, response.json()) == (403, FORBIDDEN_OWNER)
    assert "Trainer notes" not in response.text


def test_get_tasks_error_403_empty_owner_is_forbidden(client: TestClient) -> None:
    response = client.get("/api/tasks", params={"owner": ""}, headers=auth())
    assert (response.status_code, response.json()) == (403, FORBIDDEN_OWNER)


# --------------------------------------------------------------- POST /api/tasks


def test_post_tasks_happy_path_creates_and_persists_task(client: TestClient) -> None:
    payload = {"title": "Write docs", "description": "Document the API", "status": "IN_PROGRESS", "priority": "HIGH"}
    response = client.post("/api/tasks", headers=auth(), json=payload)
    assert response.status_code == 201
    assert _without_created_at(response.json()) == {"id": FIRST_CREATED_TASK_ID, "owner": "student", **payload}
    assert CREATED_AT_FORMAT.match(response.json()["createdAt"])
    listed = client.get("/api/tasks", headers=auth()).json()
    assert _without_created_at(listed[-1]) == _without_created_at(response.json())


def test_post_tasks_edge_empty_object_uses_defaults(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={})
    assert response.status_code == 201
    assert _without_created_at(response.json()) == {
        "id": FIRST_CREATED_TASK_ID, "title": "", "description": "", "status": "TODO", "owner": "student", "priority": "MEDIUM",
    }


def test_post_tasks_edge_unknown_fields_are_ignored(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "x", "unexpected": 1})
    assert response.status_code == 201
    assert "unexpected" not in response.json()


def test_post_tasks_edge_null_owner_means_own_user(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "x", "owner": None})
    assert (response.status_code, response.json()["owner"]) == (201, "student")


def test_post_tasks_edge_unicode_and_long_text_are_stored_intact(client: TestClient) -> None:
    title = "Revisión ñandú 日本語 " + "x" * 5000
    created = client.post("/api/tasks", headers=auth(), json={"title": title}).json()
    assert created["title"] == title
    assert client.get("/api/tasks", headers=auth()).json()[-1]["title"] == title


def test_post_tasks_error_401_without_token_even_with_invalid_body(client: TestClient) -> None:
    response = client.post("/api/tasks", json={"title": ["x"]})
    assert (response.status_code, response.json()) == (401, INVALID_TOKEN)


def test_post_tasks_error_403_creating_for_another_owner(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "x", "owner": "trainer"})
    assert (response.status_code, response.json()) == (403, FORBIDDEN_OWNER)
    assert len(client.get("/api/tasks", headers=auth("trainer")).json()) == 1


def test_post_tasks_error_403_empty_owner_is_forbidden(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"owner": ""})
    assert (response.status_code, response.json()) == (403, FORBIDDEN_OWNER)


@pytest.mark.parametrize(
    ("body", "error_type", "location"),
    [
        ({"title": ["x"]}, "string_type", ["body", "title"]),
        ({"title": None}, "string_type", ["body", "title"]),
        ({"description": 5}, "string_type", ["body", "description"]),
        ({"status": None}, "string_type", ["body", "status"]),
        ({"priority": {"a": 1}}, "string_type", ["body", "priority"]),
        ({"owner": 7}, "string_type", ["body", "owner"]),
    ],
    ids=["title-list", "title-null", "description-number", "status-null", "priority-object", "owner-number"],
)
def test_post_tasks_error_422_field_with_wrong_type(client: TestClient, body: dict, error_type: str, location: list[str]) -> None:
    response = client.post("/api/tasks", headers=auth(), json=body)
    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert (error["type"], error["loc"]) == (error_type, location)


def test_post_tasks_error_422_without_body(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth())
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "missing"
    assert response.json()["detail"][0]["loc"] == ["body"]


def test_post_tasks_error_422_malformed_json(client: TestClient) -> None:
    response = client.post("/api/tasks", headers={**auth(), "Content-Type": "application/json"}, content=b"{bad")
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "json_invalid"


def test_post_tasks_error_422_form_body_instead_of_json(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), data={"title": "x"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "model_attributes_type"


def test_post_tasks_422_does_not_create_a_task(client: TestClient) -> None:
    client.post("/api/tasks", headers=auth(), json={"title": None})
    assert len(client.get("/api/tasks", headers=auth()).json()) == 2


# ------------------------------------------------------------- GET /api/summary


def test_get_summary_happy_path_after_creating_tasks(client: TestClient) -> None:
    client.post("/api/tasks", headers=auth(), json={"title": "a", "status": "DONE", "priority": "HIGH"})
    client.post("/api/tasks", headers=auth(), json={"title": "b", "status": "TODO", "priority": "HIGH"})
    assert client.get("/api/summary", headers=auth()).json() == {
        "owner": "student", "total": 4, "byStatus": {"TODO": 2, "IN_PROGRESS": 1, "DONE": 1}, "highPriorityOpen": 2,
    }


def test_get_summary_edge_user_without_tasks(client: TestClient) -> None:
    response = client.get("/api/summary", headers=auth("nobody"))
    assert (response.status_code, response.json()) == (200, {"owner": "nobody", "total": 0, "byStatus": {}, "highPriorityOpen": 0})


def test_get_summary_edge_other_users_tasks_are_not_counted(client: TestClient) -> None:
    client.post("/api/tasks", headers=auth("trainer"), json={"title": "t", "priority": "HIGH"})
    assert client.get("/api/summary", headers=auth()).json()["total"] == 2
    assert client.get("/api/summary", headers=auth("trainer")).json()["total"] == 2


def test_get_summary_edge_free_text_status_is_counted_and_priority_is_case_sensitive(client: TestClient) -> None:
    client.post("/api/tasks", headers=auth("nobody"), json={"title": "t", "status": "custom", "priority": "high"})
    body = client.get("/api/summary", headers=auth("nobody")).json()
    assert (body["byStatus"], body["highPriorityOpen"]) == ({"custom": 1}, 0)


def test_get_summary_error_401_without_token(client: TestClient) -> None:
    response = client.get("/api/summary")
    assert (response.status_code, response.json()) == (401, INVALID_TOKEN)


def test_get_summary_error_403_user_cannot_read_summary_of_another_owner(client: TestClient) -> None:
    response = client.get("/api/summary", params={"owner": "trainer"}, headers=auth())
    assert (response.status_code, response.json()) == (403, FORBIDDEN_OWNER)


def test_get_summary_error_403_empty_owner_is_forbidden(client: TestClient) -> None:
    response = client.get("/api/summary", params={"owner": ""}, headers=auth())
    assert (response.status_code, response.json()) == (403, FORBIDDEN_OWNER)


# ------------------------------------------------------- POST /api/requirements


def test_post_requirements_happy_path_stores_file_and_returns_contract(client: TestClient, tmp_path: Path) -> None:
    response = _upload(client, TEXT_FILE)
    assert response.status_code == 201
    assert response.json() == {
        "owner": "student",
        "fileName": "requirements.txt",
        "storedAt": str(tmp_path / "uploads" / "requirements.txt"),
        "size": 24,
    }
    assert (tmp_path / "uploads" / "requirements.txt").read_bytes() == TEXT_FILE[1]


def test_post_requirements_edge_file_without_extension_is_accepted(client: TestClient, tmp_path: Path) -> None:
    response = _upload(client, ("README", b"no extension", "application/octet-stream"))
    assert (response.status_code, response.json()["fileName"]) == (201, "README")
    assert (tmp_path / "uploads" / "README").read_bytes() == b"no extension"


def test_post_requirements_edge_empty_file_has_size_zero(client: TestClient, tmp_path: Path) -> None:
    response = _upload(client, ("empty.txt", b"", "text/plain"))
    assert (response.status_code, response.json()["size"]) == (201, 0)
    assert (tmp_path / "uploads" / "empty.txt").read_bytes() == b""


def test_post_requirements_edge_binary_content_is_stored_byte_for_byte(client: TestClient, tmp_path: Path) -> None:
    content = bytes(range(256)) * 4096
    response = _upload(client, ("data.bin", content, "application/octet-stream"))
    assert (response.status_code, response.json()["size"]) == (201, 1024 * 1024)
    assert (tmp_path / "uploads" / "data.bin").read_bytes() == content


def test_post_requirements_edge_file_with_same_name_is_overwritten(client: TestClient, tmp_path: Path) -> None:
    _upload(client, ("same.txt", b"first", "text/plain"))
    _upload(client, ("same.txt", b"second", "text/plain"))
    assert (tmp_path / "uploads" / "same.txt").read_bytes() == b"second"


def test_post_requirements_edge_filename_with_spaces(client: TestClient, tmp_path: Path) -> None:
    response = _upload(client, ("my requirements v1.txt", b"x", "text/plain"))
    assert (response.status_code, response.json()["fileName"]) == (201, "my requirements v1.txt")
    assert (tmp_path / "uploads" / "my requirements v1.txt").exists()


def test_post_requirements_error_401_without_token(client: TestClient, tmp_path: Path) -> None:
    response = client.post("/api/requirements", files={"file": TEXT_FILE})
    assert (response.status_code, response.json()) == (401, INVALID_TOKEN)
    assert not (tmp_path / "uploads" / "requirements.txt").exists()


def test_post_requirements_error_401_with_invalid_token(client: TestClient) -> None:
    response = _upload(client, TEXT_FILE, bearer("not-a-token"))
    assert (response.status_code, response.json()) == (401, INVALID_TOKEN)


def test_post_requirements_error_422_without_file_field(client: TestClient) -> None:
    response = client.post("/api/requirements", headers=auth())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]
    assert response.json()["detail"][0]["type"] == "missing"


def test_post_requirements_error_422_part_without_filename(client: TestClient) -> None:
    response = _upload(client, ("", b"x", "text/plain"))
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


@pytest.mark.xfail(strict=True, reason="H-API-04 pendiente: el nombre del cliente se usa como ruta (path traversal)")
def test_post_requirements_security_traversal_name_stays_inside_upload_dir(client: TestClient, tmp_path: Path) -> None:
    _upload(client, ("../escape.txt", b"x", "text/plain"))
    assert not (tmp_path / "escape.txt").exists()


# ------------------------------------------------------ GET /api/backend-health


def test_get_backend_health_happy_path_relays_upstream_json(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    with health_server(200, b'{"status":"UP","checks":[]}') as url:
        monkeypatch.setenv("AUTH_HEALTH_URL", url)
        response = client.get("/api/backend-health", headers=auth("trainer"))
    assert (response.status_code, response.json()) == (
        200,
        {"requestedBy": "trainer", "status": 200, "body": '{"status":"UP","checks":[]}'},
    )


def test_get_backend_health_edge_upstream_error_status_is_relayed_with_http_200(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    with health_server(503, b"DOWN") as url:
        monkeypatch.setenv("AUTH_HEALTH_URL", url)
        response = client.get("/api/backend-health", headers=auth())
    assert (response.status_code, response.json()) == (200, {"requestedBy": "student", "status": 503, "body": "DOWN"})


def test_get_backend_health_edge_empty_upstream_body(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    with health_server(204, b"") as url:
        monkeypatch.setenv("AUTH_HEALTH_URL", url)
        body = client.get("/api/backend-health", headers=auth()).json()
    assert (body["status"], body["body"]) == (204, "")


def test_get_backend_health_edge_non_utf8_body_is_decoded_with_replacement(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    with health_server(200, b"ok \xff\xfe") as url:
        monkeypatch.setenv("AUTH_HEALTH_URL", url)
        response = client.get("/api/backend-health", headers=auth())
    assert (response.status_code, response.json()["body"]) == (200, "ok \ufffd\ufffd")


def test_get_backend_health_edge_unreachable_backend_returns_http_200_status_zero(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://127.0.0.1:1/q/health")
    response = client.get("/api/backend-health", headers=auth())
    assert (response.status_code, response.json()) == (200, {"requestedBy": "student", "status": 0, "body": "Backend unavailable"})


def test_get_backend_health_error_401_without_token(client: TestClient) -> None:
    response = client.get("/api/backend-health")
    assert (response.status_code, response.json()) == (401, INVALID_TOKEN)


def test_get_backend_health_client_cannot_choose_the_url(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://127.0.0.1:1/q/health")
    response = client.get("/api/backend-health", params={"url": "http://example.invalid"}, headers=auth())
    assert response.json()["body"] == "Backend unavailable"


# ------------------------------------------- errores comunes a todos los endpoints


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_every_endpoint_error_500_when_jwt_secret_is_not_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, method: str, path: str
) -> None:
    headers = auth()
    monkeypatch.delenv("WORKSHOP_JWT_SECRET")
    response = getattr(client, method)(path, headers=headers)
    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    assert response.headers["content-type"].startswith("text/plain")


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_every_endpoint_error_401_body_is_generic_for_invalid_tokens(client: TestClient, method: str, path: str) -> None:
    for headers in (bearer("not-a-token"), bearer(make_token(ttl=-10)), {"Authorization": "Basic abc"}):
        response = getattr(client, method)(path, headers=headers)
        assert (response.status_code, response.json()) == (401, INVALID_TOKEN)


@pytest.mark.parametrize(("method", "path"), [("delete", "/api/tasks"), ("put", "/api/summary"), ("get", "/api/requirements"), ("post", "/api/backend-health")])
def test_error_405_for_methods_not_offered(client: TestClient, method: str, path: str) -> None:
    response = getattr(client, method)(path, headers=auth())
    assert (response.status_code, response.json()) == (405, {"detail": "Method Not Allowed"})
```
