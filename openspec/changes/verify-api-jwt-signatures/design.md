# Design

## Context

Para la motivación y los requisitos comprometidos, véanse [proposal.md](./proposal.md) y [spec.md](./specs/api-authentication/spec.md). El baseline de comportamiento es `docs/ENDPOINTS.md`.

La API ya centraliza la lectura de `Authorization`, la configuración externa y la verificación de identidad en `api/app/security.py`; `api/app/routes.py` inyecta esa dependencia en las cinco rutas protegidas. La configuración de despliegue se suministra a través de variables de entorno en `compose.yaml`. Las pruebas de `api/tests/test_api.py` ya usan claves RSA efímeras y cubren varios casos de firma, claims, credenciales legacy y configuración ausente. El diseño preserva este límite, evita introducir un segundo mecanismo de autenticación y no requiere una dependencia nueva.

## Goals / Non-Goals

**Goals:**

- Mantener una única frontera de autenticación compartida por las rutas protegidas.
- Hacer que la identidad autenticada provenga de `sub` de un JWT RS256 verificado y de configuración externa.
- Mantener diferenciados los errores de credenciales (`401`) y de configuración no disponible (`503`).
- Completar la caracterización observable de rutas, respuestas y fallos antes de cambiar comportamiento crítico.

**Non-Goals:**

- Cambiar la emisión de tokens en `auth/` o integrar el flujo real entre `auth/` y `api/`.
- Rediseñar la autorización por propietario, los repositorios o la estructura de la aplicación.
- Cambiar contratos de `web/`, rutas, respuestas exitosas o esquemas ajenos al alcance de esta change.
- Agregar proveedores de identidad, descubrimiento de claves, rotación/JWKS o una dependencia JWT adicional.

## Impact

- **API:** frontera de autenticación existente en `api/app/security.py` y dependencias de las rutas en `api/app/routes.py`.
- **Pruebas:** caracterización de seguridad y compatibilidad en `api/tests/test_api.py`.
- **Despliegue/documentación:** variables externas existentes en `compose.yaml` y contrato en `docs/ENDPOINTS.md`.
- **Sin cambios:** `auth/`, `web/` y las secciones generales que documenten esos componentes.

## Contratos protegidos

- Las rutas protegidas siguen siendo `GET /api/tasks`, `POST /api/tasks`, `GET /api/summary`, `POST /api/requirements` y `GET /api/backend-health`, con sus métodos, paths, headers, respuestas exitosas y formatos documentados en `docs/ENDPOINTS.md`.
- El cliente continúa enviando la credencial con el esquema Bearer. La API no acepta el formato Base64 legacy.
- Credenciales ausentes o inválidas responden `401` con `{"detail":"Invalid token"}`; configuración JWT ausente o inválida responde `503` con `{"detail":"Authentication configuration unavailable"}`.
- `sub` identifica al solicitante. `role` puede estar ausente y no concede autorización por sí mismo; las reglas existentes de propietario no cambian.
- Ningún token, credencial ni material de clave debe aparecer en logs o documentación.

## Decisions

### Una dependencia compartida como frontera de autenticación

Se conserva la verificación en el dependency de FastAPI ya compartido por las cinco rutas, y se evita repartir validaciones entre handlers.

- **Alternativa considerada:** implementar validación separada en cada endpoint o envolver el router con un esquema distinto. Se descarta porque duplica reglas y permite respuestas inconsistentes o rutas olvidadas.
- **Consecuencia:** la prueba de cobertura de rutas debe fallar si alguna de las cinco rutas deja de aplicar la dependencia.

### Verificación RS256 con valores de confianza externos

Se acepta solo RS256 y se valida la firma y los claims `sub`, `iss`, `aud` y `exp` con la clave pública, emisor y audiencia suministrados por `AUTH_JWT_PUBLIC_KEY`, `AUTH_JWT_ISSUER` y `AUTH_JWT_AUDIENCE`. La identidad se deriva de `sub`; los valores confiables no se toman del token.

- **Alternativa considerada:** conservar el token Base64 legacy o permitir que el algoritmo se seleccione desde el header del token. Se descarta: ninguna opción demuestra la identidad acordada por la spec.
- **Alternativa considerada:** añadir un servicio JWKS o integrar el emisor de `auth/`. Se descarta por fuera de alcance y porque agregaría dependencia operativa no requerida por el Issue.
- **Consecuencia:** el despliegue debe proporcionar la configuración correcta; si no está disponible, la API falla de forma explícita con el `503` documentado.

### Separar errores de configuración y errores de credencial

La entrada Bearer ausente o malformada y los tokens con firma o claims inválidos se tratan como credenciales inválidas (`401`). La configuración incompleta o una clave pública no utilizable se trata como indisponibilidad de configuración (`503`). Se conserva el contrato de prioridad ya caracterizado: si no hay credencial, se responde `401` aunque falte configuración.

- **Alternativa considerada:** responder `401` en todos los fallos para no revelar el estado del servicio. Se descarta porque contradice el contrato documentado y oculta un problema de despliegue distinto de una credencial incorrecta.
- **Alternativa considerada:** responder `503` antes de inspeccionar la autorización. Se descarta porque cambiaría el caso documentado/caracterizado de ausencia de autorización.

### Usar configuración de despliegue, no secretos en el repositorio

Compose continúa pasando las tres variables al servicio API desde el entorno de despliegue, sin agregar valores reales ni almacenar material privado en el repositorio. La clave pública puede representarse con saltos de línea escapados tal como contempla el contrato.

- **Alternativa considerada:** codificar claves o valores de issuer/audience en la imagen o en código. Se descarta porque acopla credenciales de despliegue a artefactos versionados.
- **Consecuencia:** los entornos deben documentar y suministrar los valores; las pruebas usan claves temporales aisladas.

## Estrategia incremental

1. **Caracterizar antes del cambio:** fijar con pruebas los status, cuerpos y ausencia de ejecución de operaciones ante fallos de autenticación; comprobar respuestas exitosas existentes en las cinco rutas.
2. **Completar la cobertura de la frontera:** añadir casos que falten para configuración incompleta/inválida, claims requeridos, firma incorrecta, formato legacy, PEM con saltos escapados y ausencia de filtración de credenciales en logs. Usar claves RSA efímeras y valores de prueba; no usar secretos reales.
3. **Ajustar solo la autenticación de la API si la caracterización evidencia una brecha:** preservar la dependencia común, la identidad derivada de `sub`, el mapeo `401`/`503` y las reglas de autorización existentes. No refactorizar rutas ni capas no necesarias.
4. **Verificar el contrato integrado:** ejecutar las pruebas de `api/` y comprobar que la configuración de Compose y `docs/ENDPOINTS.md` siguen nombrando las variables y respuestas comprometidas, sin alterar sus secciones de `auth/` o `web/`.

## Pruebas de caracterización necesarias

Antes de modificar el verificador o el comportamiento de rutas, establecer estas pruebas en `api/tests/test_api.py`:

- **Aceptación:** JWT RS256 válido con `sub`, `iss`, `aud` y `exp` correctos permite que cada ruta protegida conserve su respuesta exitosa documentada.
- **Rechazo de credenciales:** ausencia/header malformado, Base64 legacy, JWT malformado, expirado, con issuer/audience incorrectos, claims requeridos ausentes o firma hecha con otra clave producen `401` y el cuerpo exacto documentado.
- **Configuración:** falta individual de cualquiera de las variables o clave pública no utilizable produce `503` para una credencial presente; una autorización ausente sigue produciendo `401`, incluso si falta configuración.
- **PEM:** la representación con `\\n` verifica una firma válida.
- **Sin efectos ante rechazo:** una solicitud que acaba en `401` o `503` no ejecuta la operación protegida (escritura, carga o consulta al backend).
- **Sin exposición:** los logs generados por credenciales inválidas y configuración inválida no contienen el token, credencial ni material de clave.
- **Compatibilidad de rutas:** afirmar método, path, status exitoso y forma del cuerpo para las cinco operaciones; mantener aparte las pruebas existentes de autorización por `owner`.

Ejecutar la suite desde `api/` y comprobar que las pruebas usan claves temporales generadas en memoria o fixtures aislados. No depender de credenciales de entorno de producción.

## Riesgos / Trade-offs

- **Configuración inválida bloquea todas las rutas protegidas** → validar las tres variables y la clave pública en el despliegue; mantener el `503` explícito, sin degradar a aceptación legacy.
- **Pruebas incompletas dejan una ruta sin proteger o cambian su respuesta** → usar una matriz común sobre las cinco rutas y aserciones exactas de status/cuerpo más pruebas de éxito.
- **Uso accidental de datos sensibles en pruebas o logs** → generar claves efímeras locales, evitar registrar headers/claims completos y comprobar explícitamente la salida de logs.
- **La resolución por entorno no aporta rotación dinámica ni JWKS** → se acepta como límite del Issue; rotación/JWKS requeriría una propuesta separada.
- **Un cambio de orden entre validación de header y configuración altera el error observado** → caracterizar expresamente el `401` por autorización ausente antes de cualquier cambio.

## Migration Plan y rollback

No se requiere migración de datos. Desplegar primero la configuración externa de la API y verificar que contiene clave pública, issuer y audience compatibles; después desplegar la API con las pruebas de contrato pasando. Si el despliegue falla por configuración, corregirla o revertir la versión de la API al artefacto anterior. No habilitar un fallback Base64 para recuperar servicio: si el entorno previo dependía de ese formato, detener la integración y resolverlo como cambio de alcance explícito antes del despliegue.

## Decisiones abiertas

No quedan decisiones de arquitectura pendientes para implementar el alcance actual. La estrategia de rotación de claves o adopción futura de JWKS queda fuera de esta change y requiere una decisión separada.
