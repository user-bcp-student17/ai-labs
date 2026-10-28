---
name: pr-testing-review
description: 'Revisa la calidad y suficiencia de las pruebas de un PR. Usa para comprobar si los cambios están cubiertos por pruebas relevantes, incluidos casos límite y errores; fija base/cabeza con SHA y entrega un informe local sin publicar la revisión.'
argument-hint: '[owner/repo] [número de PR]'
---

# Revisión de pruebas de PR

Revisa exclusivamente si las pruebas del PR verifican adecuadamente los comportamientos que cambia. No conviertas esta revisión en una auditoría general de código y no publiques una revisión, comentario, aprobación ni release.

## Criterio

Comprueba que las pruebas añadidas o modificadas ejerciten los comportamientos nuevos o alterados y sus resultados observables, incluidos casos válidos, límites y errores pertinentes. Considera una omisión un defecto solo si el diff y el contrato demuestran una ruta de comportamiento afectada sin verificación suficiente; clasifica como riesgo lo que dependa de requisitos o escenarios no especificados.

## Procedimiento

1. **Fija el objeto de revisión.**
   - Identifica `owner/repo` y el número del PR solicitado. Si no se indican, usa el repositorio actual y el PR señalado inequívocamente; si hay más de uno, pide aclaración.
   - Consulta el PR, sus metadatos y el diff mediante GitHub MCP. Registra URL, ref/SHA completo de base y ref/SHA completo de cabeza.
   - Si la respuesta no incluye SHA, resuelve las refs con MCP. Basa la revisión solo en el diff de esas versiones.

2. **Examina las pruebas junto con los cambios que verifican.**
   - Revisa los hunks de producción y de pruebas del diff para identificar las rutas funcionales afectadas, contratos y resultados esperados.
   - Consulta contexto adicional mediante MCP en el SHA de base o cabeza correspondiente, e indica cuál consultaste. No uses el checkout local como evidencia de la versión del PR.
   - Comprueba si hay aserciones observables para comportamiento exitoso, entradas límite y errores relevantes, y si las pruebas fallarían ante una regresión razonable del comportamiento cambiado.
   - Evalúa claridad y aislamiento de las pruebas, sin revisar estilo o calidad ajenos a su capacidad de verificar los cambios.

3. **Distingue brechas demostradas de riesgos.**
   - Cita por observación una ruta y línea del diff de cabeza o un fragmento literal localizable.
   - Marca **Defecto demostrado** si un comportamiento cambiado y respaldado por contrato queda sin prueba adecuada o si una prueba tiene una expectativa que contradice dicho contrato.
   - Marca **Riesgo que requiere confirmación** si no se puede determinar la expectativa o criticidad por falta de requisitos, consumidor o contexto.
   - Para cada observación di qué prueba o aserción añadir/ejecutar permitiría confirmarla o cerrarla. No inventes cobertura ni afirmes que una regresión ocurrió sin evidencia.

4. **Registra la ejecución con precisión.**
   - Inspeccionar código de pruebas no equivale a ejecutarlas. Si decides ejecutar una prueba focalizada y el entorno lo permite, registra comando exacto, directorio y resultado.
   - Si no se ejecutaron pruebas, dilo expresamente. No declares passed, cobertura ni resultado de CI basándote únicamente en el cuerpo del PR.
   - Explica qué áreas de pruebas examinaste aunque no encuentres observaciones.

5. **Entrega un informe local.**
   - Guarda `REVISION-PR-<número>-pruebas.md` en la raíz, salvo que se solicite otra ruta.
   - Incluye URL del PR, SHA completos, criterio, observaciones con evidencia diff, pruebas ejecutadas/no ejecutadas e incertidumbres.
   - No publiques ni cambies el PR.

## Formato sugerido

```markdown
# Revisión de pruebas — PR #N

- PR: [#N — título](URL)
- Base: `ref` (`SHA completo`)
- Cabeza: `ref` (`SHA completo`)
- Criterio: suficiencia de pruebas para el comportamiento modificado

## Observaciones

### [Defecto demostrado | Riesgo que requiere confirmación] — resumen
- Evidencia del diff: `ruta:línea` o fragmento literal.
- Brecha/impacto de verificación: ...
- Prueba que lo confirma o cierra: ...

## Comprobaciones
- Pruebas inspeccionadas: ...
- Comandos ejecutados y resultados reales: ... / No se ejecutaron pruebas.
- Alcance no cubierto e incertidumbres: ...

La revisión es local; no se publicó ni constituye aprobación del PR.
```
