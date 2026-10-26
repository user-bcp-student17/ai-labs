# Plan de correccion

## API

### Aprobación humana
- Rodolfo
- 2026-10-26
- De H-API-01 a H-API-07

### Decision de contrato acordada

- **API — H-API-02:** el usuario solicito rechazar con `403` los listados/resumenes que pidan un `owner` distinto a la identidad autenticada y las creaciones cuyo `owner` explicito no coincida. Las rutas y respuestas para el propietario autenticado se conservan.
- **API — H-API-03:** el usuario confirmo permitir solo `.txt`, limitar cargas a 1 MiB, devolver `400` para nombre/extensión no permitidos y `413` para archivos que superen el limite.


### Seleccion y prioridad

Se incluyen H-API-01 a H-API-07 porque son todos los hallazgos de api que aparecen como `Pendiente` en `HALLAZGOS.md`. Se priorizan primero los cuatro de severidad alta (SQL, autorizacion, archivos y token), despues los dos de severidad media (arquitectura y calidad) y al final la revision SCA de severidad baja. La aprobacion humana registrada cubre los siete IDs.

### Contrato observado y limites

`docs/ENDPOINTS.md` no existe. El comportamiento observado en `api/app/main.py` es:

- `GET /api/tasks`: acepta `owner` opcional, usa el usuario del token si falta y devuelve una lista con `id`, `title`, `description`, `status`, `owner`, `priority` y `createdAt`.
- `POST /api/tasks`: acepta un objeto JSON, devuelve `201` y la tarea creada.
- `GET /api/summary`: acepta `owner` opcional y devuelve `owner`, `total`, `byStatus` y `highPriorityOpen`.
- `POST /api/requirements`: recibe multipart `file`, devuelve `201` con `owner`, `fileName`, `storedAt` y `size`.
- `GET /api/backend-health`: consulta la URL configurada y devuelve `requestedBy`, `status` y `body`.
- La autenticacion espera `Authorization: Bearer ...`; hoy decodifica Base64 con formato propio y responde `401` ante token invalido.

Las pruebas actuales cubren solo parte de esos resultados en `api/tests/test_api.py:19-58`. Se propone conservar rutas, codigos y formas JSON de los casos validos caracterizados. Para H-API-02 se acordo responder `403` ante un propietario distinto y para H-API-03 se acordo la politica `.txt`/1 MiB/400/413. H-API-04 sigue sin contrato JWT acordado. No se crea `docs/ENDPOINTS.md` en este paso.

### H-API-01 — SQL concatenado

- **Hallazgo y problema:** los filtros y el `INSERT` construyen SQL con valores de entrada (`api/app/main.py:70,84`). Comillas u otros valores pueden romper o alterar la consulta.
- **Cambio propuesto:** mover acceso a datos a un repositorio y usar parametros de SQLite para todos los valores; conservar columnas, orden, reglas y respuestas actuales.
- **Archivos a tocar:** `api/app/main.py`, `api/tests/test_api.py`; crear `api/app/repositories.py` si se aprueba separar persistencia.
- **Caracterizacion antes del cambio:** ampliar `api/tests/test_api.py` con lectura, creacion y resumen para datos normales; agregar titulo y descripcion con apostrofe y comprobar `201`, los campos existentes y que los valores vuelvan literalmente al consultar. Ejecutar desde `api/` con `python -m pytest`.

### H-API-02 — Autorizacion por propietario

- **Hallazgo y problema:** `owner` de query y del cuerpo puede sustituir al usuario autenticado (`api/app/main.py:69,83,92`).
- **Cambio propuesto:** usar exclusivamente `identity["username"]` para seleccionar y asignar propietario, conforme a `docs/GOOD_PRACTICES.md`. Rechazar con `403` un `owner` distinto tanto en query como en el cuerpo. Mantener las rutas y respuestas para solicitudes del propio usuario.
- **Archivos a tocar:** `api/app/main.py`, `api/tests/test_api.py`; `api/app/repositories.py` si se separa persistencia.
- **Caracterizacion antes del cambio:** con token `student` y `owner=trainer`, las pruebas observaron `200` en listado/resumen y `201` en creacion. Tras el acuerdo de `403`, las mismas peticiones deben rechazarse y la creacion no debe insertar una tarea; las pruebas de rutas normales verifican que el propietario autenticado conserva su comportamiento.

### H-API-03 — Carga de archivos

- **Hallazgo y problema:** el nombre recibido se usa en la ruta destino y el archivo se lee completo (`api/app/main.py:109-111`); no se observan controles de extension o tamano.
- **Cambio propuesto:** permitir solo `.txt`, rechazar separadores/rutas en el nombre, normalizar el nombre y limitar la lectura a 1 MiB. Responder `400` para nombre/extensión no permitidos y `413` para tamaño excesivo. Mantener `POST /api/requirements`, el `201` y las claves actuales de respuesta para cargas aceptadas. Usar constantes con nombre, no limites magicos.
- **Archivos a tocar:** `api/app/main.py`, `api/tests/test_api.py`; crear `api/app/upload_service.py` solo si se separa esa responsabilidad.
- **Caracterizacion antes del cambio:** comprobar status, cuerpo y bytes guardados para `requirements.txt`; probar `../escape.txt`, extension `.pdf` y contenido de 1 MiB + 1. Antes del cambio se espera que el comportamiento actual los acepte o falle de forma no controlada; despues deben dar los status acordados y no escribir fuera del directorio.

### H-API-04 — Token sin firma verificable

- **Hallazgo y problema:** el token es Base64 con secreto fijo; se comprueba el vencimiento, pero no una firma JWT, emisor o audiencia (`api/app/main.py:14,20,22`).
- **Cambio propuesto:** adoptar verificacion JWT de firma, emisor, audiencia y expiracion; obtener la clave de configuracion externa y no incluir secretos reales. Una biblioteca JWT mantenida (por ejemplo PyJWT) estaria justificada por la verificacion criptografica requerida, pero su inclusion y version deben pasar revision SCA antes de agregarse a `api/requirements.txt`.
- **Archivos a tocar:** `api/app/main.py`, `api/tests/test_api.py`, `api/requirements.txt` si se aprueba la dependencia; crear `api/app/security.py` para aislar la verificacion.
- **Caracterizacion antes del cambio:** ampliar la prueba de token invalido (`api/tests/test_api.py:54-58`) y registrar status y estructura de error de tokens aceptados, malformados y vencidos. Para la nueva verificacion, probar firma invalida, `exp`, `iss` y `aud` con secretos ficticios.
- **Bloqueo de contrato:** el token actual usa un formato propio y no hay `docs/ENDPOINTS.md`. No se leyo el componente emisor por el limite de alcance. El usuario indico que proporcionara el perfil JWT del emisor; hasta recibir algoritmo, `iss`, `aud`, claims y configuracion de clave, no cambiar la aceptacion de tokens.

### H-API-05 — Responsabilidades concentradas

- **Hallazgo y problema:** `api/app/main.py` mezcla identidad, ciclo de vida SQLite, serializacion, endpoints, reglas de resumen y archivos (`api/app/main.py:17,29,56,67,77,90,107,114`).
- **Cambio propuesto:** separar rutas, esquemas, servicios y repositorio; cada funcion debe tener una responsabilidad, reutilizar el mapeo/consultas comunes y usar guard clauses donde reduzcan anidamiento. Mantener rutas y contratos observados.
- **Archivos a tocar:** `api/app/main.py`, `api/tests/test_api.py`; crear modulos bajo `api/app/` para `schemas`, `services`, `repositories` y, si sigue siendo necesario, carga/seguridad.
- **Caracterizacion antes del cambio:** ampliar la suite con pruebas de status, campos y valores de cada ruta local, usando SQLite y archivos temporales; conservar las cuatro pruebas actuales como regresion (`api/tests/test_api.py:19-58`). Ejecutar desde `api/` con `python -m pytest` antes y despues de extraer modulos.

### H-API-06 — Tipado y complejidad

- **Hallazgo y problema:** se usan `dict[str, Any]`, capturas `Exception`, condiciones anidadas y una proyeccion SQL repetida (`api/app/main.py:25,56,70,78,87,94,97-103,120`).
- **Cambio propuesto:** definir modelos Pydantic de entrada y salida; reemplazar capturas amplias por errores esperados y mensajes genericos; extraer el conteo del resumen y reutilizar la proyeccion de tarea. Conservar campos, defaults y formatos actuales para entradas validas; definir y probar explicitamente la respuesta para entradas invalidas antes de cambiar validaciones.
- **Archivos a tocar:** `api/app/main.py`, `api/tests/test_api.py`; crear `api/app/schemas.py` y modulos de servicio/repositorio segun H-API-05.
- **Caracterizacion antes del cambio:** cubrir defaults y valores validos de `POST /api/tasks`, campos de tarea y agregados de `/api/summary`; agregar casos para campos ausentes, tipos inesperados y errores de backend para fijar el comportamiento actual y acordar cualquier cambio de status/mensaje. Ejecutar desde `api/` con `python -m pytest`.

### H-API-07 — Revision SCA de dependencias

- **Hallazgo y problema:** `api/requirements.txt` fija `urllib3==2.5.0` y `python-multipart==0.0.21` (`api/requirements.txt:4-5`). La version por si sola no confirma una vulnerabilidad aplicable.
- **Cambio propuesto:** consultar un informe SCA/Dependency Review disponible y registrar advisories, versiones afectadas y remediacion. Actualizar `api/requirements.txt` solo si la evidencia lo requiere; no agregar una herramienta como dependencia de runtime. Coordinar la herramienta externa antes de usarla.
- **Archivos a tocar:** `api/requirements.txt` solo si se confirma una actualizacion necesaria; `api/tests/test_api.py` para regresion de carga si cambia `python-multipart`.
- **Caracterizacion antes del cambio:** guardar el resultado de la revision SCA con herramienta/version y advisories; si se cambia una version, ejecutar las pruebas existentes de API y carga desde `api/`. No hay resultado SCA disponible en este Discovery.

### Decisiones y pendientes antes de implementar

- H-API-02: decision `403` registrada; la revision local encontro que `owner=""` se trata como ausente y devuelve 201 en creacion. Estado reabierto a Pendiente; agregar caracterizacion para owner explicito vacio y rechazarlo con 403.
- H-API-03: politica acordada; la revision local encontro que `requirements.txt:payload.txt` pasa el validador de nombre. Estado reabierto a Pendiente; rechazar `:` y cubrir nombres ADS en Windows antes de guardar.
- Acordar emisor, audiencia, claims y migracion del token JWT con el responsable del emisor; no se inspeccionaron componentes externos.
- H-API-07: pins actualizados segun advisories publicos; `pip-audit` no esta instalado, por lo que no se genero un informe automatizado.
- La documentacion indica Python 3.13; la ejecucion previa disponible fue con Python 3.14.7 y el virtualenv no tiene `pytest`. Preparar el entorno documentado antes de la caracterizacion formal.
- La aprobacion humana de Rodolfo, fechada 2026-10-26, cubre H-API-01 a H-API-07.

### Ejecuciones

- **API — H-API-01 — antes del cambio:** desde `api/`, `python -m pytest --durations=0`: 4 pasaron, 11 advertencias, en Python 3.14.7.
- **API — H-API-01 — caracterizacion antes del cambio:** `python -m pytest tests/test_api.py -k apostrophe -q`: 3 fallaron como se esperaba; insercion, listado y resumen devolvieron 500 con apostrofes.
- **API — H-API-01 — intento parcial:** tras crear el repositorio pero antes de conectar las rutas, la misma caracterizacion dio 3 fallos; se completo el cableado y se repitio.
- **API — H-API-01 — caracterizacion despues del cambio:** el mismo comando focalizado: 3 pasaron.
- **API — H-API-01 — regresion y cobertura:** `python -m pytest --cov=app --cov-report=term-missing`: 7 pasaron, 17 advertencias; cobertura de `app/main.py` 91%, `app/repositories.py` 90% y total app 91%, en Python 3.14.7. El virtualenv de `api/` no tiene `pytest` y el README pide Python 3.13; verificar de nuevo en ese entorno antes del cierre final.
- **API — H-API-02 — caracterizacion antes del cambio:** desde `api/`, `python -m pytest tests/test_api.py -k another_owner -q`: 3 fallaron como se esperaba; listado/resumen devolvieron 200 y creacion 201 ante `owner=trainer` con token `student`.
- **API — H-API-02 — caracterizacion despues del cambio:** el mismo comando focalizado: 3 pasaron; se comprobo que la creacion rechazada no aumenta el conteo del propietario `trainer`.
- **API — H-API-02 — regresion y cobertura combinada:** `python -m pytest --cov=app --cov-report=term-missing`: 10 pasaron, 23 advertencias; cobertura de `app/main.py` 91%, `app/repositories.py` 90% y total app 91%, en Python 3.14.7. Dos caracterizaciones SQL iniciales mezclaban identidad y owner distinto; se ajustaron para probar apostrofes con la identidad autenticada.
- **API — H-API-03 — caracterizacion antes del cambio:** desde `api/`, `python -m pytest tests/test_api.py -k "upload or requirement" -q`: la carga valida paso; traversal, `.pdf` y 1 MiB + 1 recibieron 201 en vez de los status acordados.
- **API — H-API-03 — caracterizacion despues del cambio:** el mismo comando focalizado: 4 pasaron; `.txt` valido conserva 201 y datos, traversal/`.pdf` responden 400 y archivo sobre 1 MiB responde 413 sin persistir.
- **API — H-API-03 — regresion y cobertura combinada:** `python -m pytest --cov=app --cov-report=term-missing`: 13 pasaron, 29 advertencias; cobertura de `app/main.py` 91%, `app/repositories.py` 90% y total app 93%, en Python 3.14.7. `upload_service.py` quedo totalmente cubierto y pytest-cov lo omitio por `skip_covered`.
- **API — H-API-05 — caracterizacion antes del refactor:** desde `api/`, `python -m pytest --cov=app --cov-report=term-missing`: 14 pasaron, 31 advertencias, cobertura total 95%; incluyo formas de respuesta y health simulado sin red.
- **API — H-API-05 — regresion despues del refactor:** el mismo comando: 14 pasaron, 31 advertencias, cobertura total 96%; rutas y formas JSON caracterizadas conservadas.
- **API — H-API-06 — caracterizacion previa:** defaults, conversion de escalares, cuerpo no objeto, token invalido y error upstream fueron observados; cuerpo no objeto devolvio 422. Una expectativa inicial de 500 fue corregida a ese comportamiento observado antes del cambio.
- **API — H-API-06 — regresion y cobertura despues:** desde `api/`, `python -m pytest --cov=app --cov-report=term-missing`: 18 pasaron, 39 advertencias; cobertura total 98% y los status/estructuras JSON cubiertos se conservaron, con detalles de error ahora genericos.
- **API — H-API-07 — revision de advisories:** GitHub [GHSA-8988-9cw3-xx77](https://github.com/advisories/GHSA-8988-9cw3-xx77) (`urllib3 <2.8.0`, corregido en 2.8.0), [GHSA-vxq7-64xx-v4gw](https://github.com/advisories/GHSA-vxq7-64xx-v4gw) (`urllib3 <2.8.0`, corregido en 2.8.0), [GHSA-38jv-5279-wg99](https://github.com/advisories/GHSA-38jv-5279-wg99) (`urllib3 <2.6.3`, corregido en 2.6.3) y [GHSA-5rvq-cxj2-64vf / CVE-2026-53539](https://github.com/advisories/GHSA-5rvq-cxj2-64vf) (`python-multipart <0.0.30`, corregido en 0.0.30). El codigo usa `PoolManager.request` sin streaming/proxy configurado y no expone endpoints `application/x-www-form-urlencoded`; se actualizaron los pins afectados como remediacion preventiva. `pip-audit` no esta instalado, por lo que no hubo informe automatizado.
- **API — H-API-07 — instalacion y regresion posterior:** en `api/.venv`, instalacion desde `requirements.txt` y `requirements-dev.txt`; versiones verificadas `urllib3 2.8.0`, `python-multipart 0.0.30`, `pip check` sin conflictos. `python -m pytest --cov=app --cov-report=term-missing`: 18 pasaron, 39 advertencias, cobertura total 98% en Python 3.14.7.
- **API — H-API-06 — verificacion final de retornos tipados:** tras cambiar las anotaciones de handlers y servicios a modelos Pydantic, `.venv\\Scripts\\python.exe -m pytest --cov=app --cov-report=term-missing`: 18 pasaron, 39 advertencias, cobertura total 98% en Python 3.14.7.
