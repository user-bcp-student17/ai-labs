---
name: pr-security-review
description: 'Revisa seguridad de un PR con evidencia del diff. Usa para identificar defectos demostrables o riesgos de seguridad en autenticación, autorización, validación, datos sensibles o dependencias; fija SHAs con GitHub MCP y entrega un informe local sin publicar la revisión.'
argument-hint: '[owner/repo] [número de PR]'
---

# Revisión de seguridad de PR

Revisa exclusivamente los cambios del PR desde la perspectiva de seguridad. Analiza el flujo de datos y los controles afectados con evidencia, sin convertir posibilidades en vulnerabilidades confirmadas. No publiques una revisión, comentario, aprobación ni release.

## Criterio

Busca defectos de seguridad introducidos o modificados por el diff que tengan impacto y un camino plausible sustentado por el código, incluidos controles de autenticación/autorización, validación de entradas, exposición de datos, gestión de secretos, criptografía, archivos, consultas e impacto de dependencias cuando el PR las modifique. Usa el contexto del mismo SHA para validar flujo y mitigaciones.

Una preocupación sin flujo/impacto demostrable es **Riesgo que requiere confirmación**, no una vulnerabilidad confirmada. No declares explotabilidad basándote solo en nombres de funciones, alertas sin verificar o la descripción del PR.

## Límites

- No generes payloads, instrucciones de explotación, automatización ofensiva ni pruebas contra sistemas reales.
- Limita las comprobaciones a inspección defensiva del diff, contexto versionado, pruebas unitarias/de seguridad locales y metadatos de dependencias pertinentes.
- No cambies el código ni reduzcas controles de CI. Las correcciones son una tarea distinta salvo petición explícita posterior.

## Procedimiento

1. **Fija el objeto de revisión.**
   - Identifica `owner/repo` y el número del PR. Si no se indican, usa el repositorio actual y el PR señalado inequívocamente; si hay varios, pregunta.
   - Consulta los detalles del PR y su diff mediante GitHub MCP. Registra URL, ref y SHA completo de base, y ref y SHA completo de cabeza.
   - Si faltan los SHA, resuelve las referencias con MCP. Revisa solo el diff de esas versiones.

2. **Analiza el cambio dentro de su contexto versionado.**
   - Identifica los archivos y controles de seguridad afectados directamente por los hunks.
   - Consulta mediante MCP los archivos relevantes a SHA base y/o cabeza para confirmar validaciones, autorización, sanitización, manejo de errores y flujo de datos. Indica qué SHA consultaste.
   - Sigue el flujo únicamente hasta el punto necesario para demostrar o descartar la observación. No amplíes a una auditoría general de áreas no tocadas.
   - Inspecciona pruebas de seguridad modificadas como evidencia de intención/cobertura, pero distingue inspección de ejecución. No confíes exclusivamente en la narrativa del PR.

3. **Valora y cita cada observación.**
   - Cada observación debe incluir una ruta y línea cambiada del lado cabeza o un fragmento literal del diff localizable, condición necesaria, impacto y control faltante/ineficaz.
   - Clasifica como **Defecto demostrado** solo si el diff y el contexto fijado muestran una violación de seguridad concreta con impacto y ruta de datos/control verificables.
   - Clasifica como **Riesgo que requiere confirmación** si falta evidencia de exposición, configuración, consumidor o alcance. Explica exactamente qué falta y cómo comprobarlo de forma defensiva.
   - Asigna severidad con criterio y confianza de 1 a 10. No infles severidad ni declares un CVE/advisory sin fuente verificada. Si no hay observaciones, informa qué controles y rutas se inspeccionaron.
   - Para cada hallazgo, especifica una prueba defensiva o revisión que lo confirmaría, sin incluir instrucciones de explotación.

4. **Registra comprobaciones y límites.**
   - Si ejecutas pruebas o herramientas locales, registra comando exacto, directorio y resultado. Si solo leíste tests o resultados declarados por el PR, atribúyelos y aclara que no se ejecutaron en esta revisión.
   - No ocultes advertencias, fallos, áreas no probadas ni incertidumbre.

5. **Entrega un informe local.**
   - Guarda `REVISION-PR-<número>-seguridad.md` en la raíz, salvo que se solicite otra ruta.
   - Incluye PR y enlace, SHAs completos, alcance, hallazgos, severidad, confianza, evidencia diff, comprobación defensiva propuesta y límites.
   - No publiques la revisión ni hagas cambios remotos.

## Formato sugerido

```markdown
# Revisión de seguridad — PR #N

- PR: [#N — título](URL)
- Base: `ref` (`SHA completo`)
- Cabeza: `ref` (`SHA completo`)
- Alcance: controles de seguridad tocados por el diff

| # | Clasificación | Severidad | Archivo y línea | Hallazgo | Confianza |
|---|---|---|---|---|---:|
| 1 | Defecto demostrado / Riesgo que requiere confirmación | Alta | `ruta:línea` | ... | 8/10 |

## Evidencia y confirmación
- Evidencia del diff/contexto: ...
- Impacto y precondiciones: ...
- Comprobación defensiva para confirmar/cerrar: ...

## Comprobaciones y límites
- Revisado: ...
- Comandos ejecutados y resultados reales: ... / No se ejecutaron pruebas.
- No comprobado: ...

La revisión es local; no se publicó ni constituye aprobación del PR.
```
