# Pruebas de API

## Matriz de casos

Todos los casos pertenecen al componente `api`. El código ejecutable completo está en [api/tests/test_api.py](../api/tests/test_api.py). `PASS` indica que el resultado coincide con la expectativa; `XFAIL` deja visible una regresión requerida que el comportamiento actual no cumple.

| Endpoint | Caso | Tipo | Resultado esperado |
|---|---|---|---|
| `GET /api/tasks` | Lista las tareas seeded del usuario autenticado (`test_lists_seeded_tasks`) | Camino feliz | `200`, lista de tareas con los siete campos documentados. |
| `GET /api/tasks` | Usuario válido sin tareas (`test_lists_tasks_for_owner_with_apostrophe`) | Borde | `200`, `[]`. |
| `GET /api/tasks` | Header ausente (`test_every_endpoint_rejects_missing_authorization`) | Error `401` | `{"detail":"Invalid token"}`. |
| `GET /api/tasks` | Query `owner=trainer` con identidad `student` (`test_rejects_listing_another_owner`) | Error `403` | `{"detail":"Owner access denied"}`; PASS. |
| `GET /api/tasks` | Repositorio falla (`test_task_endpoints_return_generic_internal_error`) | Error `500` | Status `500`, cuerpo `Internal Server Error`. |
| `POST /api/tasks` | Crea tarea válida (`test_creates_task_and_summary`) | Camino feliz | `201`, tarea con propietario autenticado. |
| `POST /api/tasks` | Objeto vacío (`test_creates_task_with_legacy_defaults`) | Borde | `201`, defaults `""`, `TODO`, `MEDIUM` y propietario autenticado. |
| `POST /api/tasks` | `owner` de otro usuario (`test_rejects_creating_task_for_another_owner`) | Error `403` | `{"detail":"Owner access denied"}` y sin inserción; PASS. |
| `POST /api/tasks` | Body array en vez de objeto (`test_non_object_task_payload_returns_validation_error`) | Error `422` | `detail` de validación para `body`; PASS. |
| `POST /api/tasks` | Header ausente (`test_every_endpoint_rejects_missing_authorization`) | Error `401` | `{"detail":"Invalid token"}`. |
| `POST /api/tasks` | Repositorio falla (`test_task_endpoints_return_generic_internal_error`) | Error `500` | Status `500`, cuerpo `Internal Server Error`. |
| `POST /api/tasks` | `owner` explícito vacío (`test_explicit_empty_task_owner_should_be_forbidden`) | Regresión de borde | Esperado `403`; **XFAIL**, el código devuelve `201` (H-API-02). |
| `GET /api/summary` | Resumen de tareas seeded y recién creada (`test_creates_task_and_summary`) | Camino feliz | `200`, `owner`, `total`, `byStatus` y `highPriorityOpen`. |
| `GET /api/summary` | Usuario válido sin tareas (`test_summarizes_tasks_for_owner_with_apostrophe`) | Borde | `200`, total `0`, mapa vacío y high-priority-open `0`. |
| `GET /api/summary` | Header ausente (`test_every_endpoint_rejects_missing_authorization`) | Error `401` | `{"detail":"Invalid token"}`. |
| `GET /api/summary` | Query `owner=trainer` con identidad `student` (`test_rejects_summarizing_another_owner`) | Error `403` | `{"detail":"Owner access denied"}`; PASS. |
| `GET /api/summary` | Repositorio falla (`test_task_endpoints_return_generic_internal_error`) | Error `500` | Status `500`, cuerpo `Internal Server Error`. |
| `POST /api/requirements` | Sube `.txt` válido (`test_uploads_requirement`) | Camino feliz | `201`, respuesta y bytes guardados coinciden. |
| `POST /api/requirements` | Archivo de 0 bytes y archivo de exactamente 1 MiB (`test_upload_accepts_empty_and_maximum_size_files`) | Borde | Ambos `201`; `size` es 0 y 1,048,576 respectivamente. |
| `POST /api/requirements` | Nombre sin extensión (`test_upload_rejects_filename_without_extension`) | Borde/error `400` | `{"detail":"Unsupported file extension"}`. |
| `POST /api/requirements` | Ruta con traversal o extensión `.pdf` (`test_rejects_upload_with_path_traversal`, `test_rejects_non_text_requirement`) | Error `400` | `Invalid file name` o `Unsupported file extension`; PASS. |
| `POST /api/requirements` | Header ausente (`test_every_endpoint_rejects_missing_authorization`) | Error `401` | `{"detail":"Invalid token"}`. |
| `POST /api/requirements` | Tamaño de 1 MiB + 1 byte (`test_rejects_oversized_requirement`) | Error `413` | `{"detail":"File is too large"}`; PASS y no persiste el archivo. |
| `POST /api/requirements` | Falta el campo multipart `file` (`test_upload_rejects_missing_file_with_validation_error`) | Error `422` | `detail[0].loc == ["body", "file"]`; PASS. |
| `POST /api/requirements` | Fallo simulado al escribir (`test_upload_returns_generic_internal_error_for_write_failure`) | Error `500` | Status `500`, cuerpo `Internal Server Error`. |
| `POST /api/requirements` | Nombre ADS `requirements.txt:payload.txt` (`test_upload_rejects_windows_alternate_data_stream_filename`) | Regresión de seguridad | Esperado `400`; **XFAIL**, el código devuelve `201` en Windows (H-API-03). |
| `GET /api/backend-health` | Upstream responde 200 (`test_reports_backend_health`) | Camino feliz | API `200`, `status` upstream `200` y body como texto. |
| `GET /api/backend-health` | Upstream responde 503 (`test_backend_health_preserves_non_success_upstream_status`) | Borde | API `200`, `status: 503` y body upstream conservado. |
| `GET /api/backend-health` | Transporte falla o body no es UTF-8 (`test_backend_health_returns_generic_error`, `test_backend_health_returns_generic_error_for_invalid_utf8`) | Borde/error controlado | API `200`, `status: 0`, mensaje genérico. |
| `GET /api/backend-health` | Header ausente (`test_every_endpoint_rejects_missing_authorization`) | Error `401` | `{"detail":"Invalid token"}`. |
| `GET /api/backend-health` | Error inesperado de upstream (`test_backend_health_returns_generic_internal_error_for_unexpected_failure`) | Error `500` | Status `500`, cuerpo `Internal Server Error`. |

## Código de pruebas

La suite completa, incluyendo los casos de camino feliz y los asserts de cada cuerpo de error, está en [api/tests/test_api.py](../api/tests/test_api.py). Los dos casos siguientes son regresiones intencionalmente estrictas: no aceptan el comportamiento defectuoso como correcto y conservan `XFAIL` visible hasta que se corrija el código.

```python
@pytest.mark.xfail(strict=True, reason="H-API-02: explicit empty owner currently falls back to identity")
def test_explicit_empty_task_owner_should_be_forbidden(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Explicit empty owner", "owner": ""},
        )
    assert response.status_code == 403


@pytest.mark.xfail(strict=True, reason="H-API-03: colon-containing filename is not rejected")
def test_upload_rejects_windows_alternate_data_stream_filename(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt:payload.txt", b"text", "text/plain")},
        )
    assert response.status_code == 400
```

El siguiente bloque contiene las pruebas adicionales de autorización, errores y límites añadidas a la suite. Se ejecuta en el mismo módulo, usando sus imports y helpers `create_app()` y `headers()`:

```python
def test_backend_health_returns_generic_error_for_invalid_utf8(monkeypatch, tmp_path: Path) -> None:
    class InvalidUtf8PoolManager:
        def request(self, method: str, url: str, timeout: float) -> SimpleNamespace:
            return SimpleNamespace(status=200, data=b"\xff")

    monkeypatch.setattr(urllib3, "PoolManager", InvalidUtf8PoolManager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 0,
        "body": "Backend health check unavailable",
    }


@pytest.mark.parametrize(
    ("method", "path", "request_data"),
    [
        ("get", "/api/tasks", {}),
        ("post", "/api/tasks", {"json": {}}),
        ("get", "/api/summary", {}),
        (
            "post",
            "/api/requirements",
            {"files": {"file": ("requirements.txt", b"", "text/plain")}},
        ),
        ("get", "/api/backend-health", {}),
    ],
)
def test_every_endpoint_rejects_missing_authorization(
    method: str, path: str, request_data: dict, tmp_path: Path
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = getattr(client, method)(path, **request_data)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


@pytest.mark.parametrize(
    ("method", "path", "request_data", "repository_method"),
    [
        ("get", "/api/tasks", {}, "list_by_owner"),
        ("post", "/api/tasks", {"json": {}}, "create"),
        ("get", "/api/summary", {}, "summary_by_owner"),
    ],
)
def test_task_endpoints_return_generic_internal_error(
    method: str,
    path: str,
    request_data: dict,
    repository_method: str,
    tmp_path: Path,
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    def raise_database_error(*args, **kwargs):
        raise RuntimeError("database details must not reach the client")

    setattr(app.state.task_repository, repository_method, raise_database_error)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = getattr(client, method)(path, headers=headers(), **request_data)
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_upload_returns_generic_internal_error_for_write_failure(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    upload_directory_file = tmp_path / "not-a-directory"
    upload_directory_file.write_text("block directory creation", encoding="utf-8")
    app.dependency_overrides[get_upload_directory] = lambda: str(upload_directory_file)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"valid text", "text/plain")},
        )
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_backend_health_returns_generic_internal_error_for_unexpected_failure(
    monkeypatch, tmp_path: Path
) -> None:
    class UnexpectedPoolManager:
        def request(self, method: str, url: str, timeout: float) -> None:
            raise RuntimeError("unexpected upstream detail")

    monkeypatch.setattr(urllib3, "PoolManager", UnexpectedPoolManager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_upload_rejects_missing_file_with_validation_error(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/requirements", headers=headers())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_upload_rejects_filename_without_extension(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements", b"text", "text/plain")},
        )
    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported file extension"}


@pytest.mark.parametrize("content_size", [0, 1024 * 1024])
def test_upload_accepts_empty_and_maximum_size_files(
    content_size: int, tmp_path: Path
) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    content = b"x" * content_size
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", content, "text/plain")},
        )
    assert response.status_code == 201
    assert response.json()["size"] == content_size
    assert (upload_dir / "requirements.txt").read_bytes() == content


def test_backend_health_preserves_non_success_upstream_status(monkeypatch, tmp_path: Path) -> None:
    class UnhealthyPoolManager:
        def request(self, method: str, url: str, timeout: float) -> SimpleNamespace:
            return SimpleNamespace(status=503, data=b"maintenance")

    monkeypatch.setattr(urllib3, "PoolManager", UnhealthyPoolManager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 503,
        "body": "maintenance",
    }
```

Los errores `500` se producen con dependencias/repositorios simulados para no depender de fallos reales de SQLite, disco o red. Los parámetros `401` recorren las cinco operaciones; las pruebas de autorización `403` comprueban que un usuario no pueda leer tareas de otro owner.

## Ejecuciones

Comandos ejecutados desde `api/`, en Windows, Python `3.14.7` (el README del proyecto recomienda Python `3.13`).

| Comando | Directorio | Código de salida | Resultado |
|---|---|---:|---|
| `python -m pytest --cov=app --cov-report=term-missing` (línea base previa a añadir casos) | `api/` | `0` | `18 passed`, 39 warnings, cobertura global `98%`. |
| `python -m pytest tests/test_api.py -k "every_endpoint or task_endpoints_return_generic_internal_error or upload_returns_generic_internal_error or backend_health_returns_generic_internal_error or upload_rejects_missing_file or filename_without_extension or accepts_empty_and_maximum or preserves_non_success" -q` | `api/` | `0` | `15 passed`. |
| `python -m pytest tests/test_api.py -k "non_object_task or another_owner or path_traversal or non_text_requirement or oversized_requirement or invalid_utf8" -q` | `api/` | `0` | `8 passed`. |
| `python -m pytest tests/test_api.py -k "explicit_empty_task_owner or alternate_data_stream" -rx -q` | `api/` | `0` | `2 xfailed` con razones H-API-02/H-API-03. |
| `python -m pytest tests/test_api.py -k "explicit_empty_task_owner or alternate_data_stream" --runxfail -q` | `api/` | `1` | 2 fallos esperados: `201 != 403` en `owner=""`; `201 != 400` para `requirements.txt:payload.txt`. Confirma los bugs, no es un gate verde. |
| `python -m pytest --cov=app --cov-report=term-missing -rx` | `api/` | `0` | `34 passed`, `2 xfailed`, 75 warnings; resultado final de regresión. |

## Cobertura

- **Alcance modificado:** solo se modificó `api/tests/test_api.py`; no se modificaron sentencias de producción. La cobertura del archivo de tests como código no aplica: la configuración de Coverage.py mide `app` (`source = ["app"]`).
- **Cobertura global de la aplicación:** `171/172` sentencias ejecutadas, `99%`, medida con `pytest-cov`/Coverage.py (`branch = true`, `--cov=app --cov-report=term-missing`). El reporte muestra 24 ramas y una línea de rama parcial; una sentencia pendiente corresponde a `api/app/repositories.py:37`.
- **Umbral:** la cobertura global observada supera 85%; no hay código de aplicación modificado al que asignar una métrica de diff independiente.
- **Advertencias:** los 75 warnings finales son deprecaciones de `FastAPI.on_event` y `starlette`/`anyio`; no son fallos de pruebas.

## Fallos

- **Fallos de regresión confirmados:** H-API-02 devuelve `201` al crear con `owner=""` aunque se acordó `403`. H-API-03 devuelve `201` y acepta en Windows `requirements.txt:payload.txt` aunque se acordó rechazar el nombre con `400`. Los tests estrictos siguen `XFAIL`; no se cambió su resultado esperado para hacerlos pasar.

## Pendientes

- **Pendiente de cobertura de entorno:** repetir el comando final con Python `3.13`, la versión recomendada por `README.md`; esta ejecución disponible usó Python `3.14.7`.
- **Pendiente de contrato/autenticación:** H-API-04 no tiene perfil JWT del emisor acordado. Las pruebas caracterizan el token Base64 legacy actual; no inventan firma, `iss`, `aud` ni claims nuevos.

## Pruebas propuestas

- Tras corregir H-API-02/H-API-03, retirar los marcadores `xfail(strict=True)` y ejecutar de nuevo la regresión completa.
- La línea no cubierta `api/app/repositories.py:37` es la rama defensiva que ocurre si no puede recargarse una fila recién insertada; no se forzó mediante una prueba que altere el contrato HTTP.

## Documentos consultados

- `README.md`
- `RETO.md`
- `docs/GOOD_PRACTICES.md`
- `docs/ENDPOINTS.md`
- `HALLAZGOS.md`
- `PLAN.md`
- `api/app/routes.py`
- `api/app/schemas.py`
- `api/app/security.py`
- `api/app/repositories.py`
- `api/app/services.py`
- `api/app/upload_service.py`
- `api/tests/test_api.py`