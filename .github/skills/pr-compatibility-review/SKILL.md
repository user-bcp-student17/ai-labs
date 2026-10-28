---
name: pr-compatibility-review
description: 'Revisa compatibilidad de un PR con evidencia del diff. Usa para comprobar contratos de API, formatos de request/response, códigos HTTP o compatibilidad de consumidores; consulta PR y versiones exactas mediante GitHub MCP y entrega un informe local sin publicarlo.'
argument-hint: '[owner/repo] [número de PR]'
---

# Revisión de compatibilidad de PR

Realiza una revisión acotada a compatibilidad entre la base y la cabeza exactas de un PR. No publiques una revisión, comentario, aprobación ni release.

## Criterio

Comprueba si el diff preserva los contratos existentes de los consumidores: endpoints y métodos, encabezados, campos y formatos de request/response, códigos HTTP y formatos de autenticación cuando correspondan. Considera un cambio de contrato un defecto solo si contradice un requisito/contrato vigente demostrado y no está declarado como cambio intencional aprobado. Si el impacto depende de consumidores, despliegues o requisitos no verificados, clasifícalo como **riesgo que requiere confirmación**, no como defecto.

## Procedimiento

1. **Fija el objeto de revisión.**
   - Identifica `owner/repo` y el número del PR solicitado. Si no se indican, usa el repositorio actual y el PR que la persona señaló o el candidato inequívoco del contexto; si hay más de uno, pide aclaración.
   - Consulta el PR y su diff mediante GitHub MCP. Registra URL, rama/ref base, SHA base completo, rama/ref cabeza y SHA cabeza completo tal como los devuelve MCP.
   - Si las referencias son movibles o la respuesta no da SHA, resuélvelas con MCP. No cambies refs durante la revisión.
   - Usa únicamente el diff entre esos SHA. No publiques comentarios de revisión en GitHub.

2. **Mantén el alcance en compatibilidad.**
   - Lee el diff completo o las secciones pertinentes para los contratos afectados.
   - Para contexto adicional, lee archivos usando el SHA base o el SHA cabeza del PR mediante MCP, según corresponda. Declara qué versión consultaste; no uses silenciosamente el checkout local ni otra rama como evidencia.
   - Compara los contratos anteriores y nuevos que el diff toca. Revisa también pruebas de contrato existentes/modificadas, pero distingue leerlas de ejecutarlas.
   - No evalúes seguridad ni calidad general del código salvo cuando una observación sea necesaria para establecer impacto de compatibilidad.

3. **Clasifica y sustenta observaciones.**
   - Cada observación debe citar ruta y línea cambiada del lado cabeza o un fragmento literal del diff que pueda localizarse. Explica consumidor/contrato afectado y consecuencia concreta.
   - Usa **Defecto demostrado** solo si el diff demuestra una violación reproducible del contrato o requisito aplicable.
   - Usa **Riesgo que requiere confirmación** cuando el impacto depende de un consumidor, proveedor, entorno o expectativa que no se pudo verificar. Indica qué evidencia falta y qué prueba o consulta resolvería la incertidumbre.
   - Si no puedes demostrar impacto, no conviertas una posibilidad en defecto. Registra supuestos e incertidumbre.
   - Para cada observación, incluye el paso de confirmación: prueba de contrato/regresión, revisión de consumidor, configuración requerida o comprobación equivalente.

4. **Registra también el alcance negativo.**
   - Explica qué contratos y cambios se comprobaron aunque no haya hallazgos.
   - Indica con claridad qué pruebas se inspeccionaron, cuáles se ejecutaron y sus resultados. Nunca afirmes que una prueba pasó si no la ejecutaste.

5. **Entrega un informe local.**
   - Guarda el informe como `REVISION-PR-<número>-compatibilidad.md` en la raíz, salvo que se solicite otra ruta.
   - Incluye URL del PR, SHA base/cabeza completos, criterio, observaciones con evidencia diff, comprobaciones realizadas/no realizadas y límites.
   - Antes de terminar, verifica que cada observación sea localizable en el diff de esas referencias y tenga una acción concreta para confirmar su impacto.

## Formato sugerido

```markdown
# Revisión de compatibilidad — PR #N

- PR: [#N — título](URL)
- Base: `ref` (`SHA completo`)
- Cabeza: `ref` (`SHA completo`)
- Criterio: ...

## Observaciones

### [Defecto demostrado | Riesgo que requiere confirmación] — resumen
- Evidencia del diff: `ruta:línea` o fragmento literal.
- Impacto de compatibilidad: ...
- Confirmación: ...

## Comprobaciones
- Revisado: ...
- Pruebas inspeccionadas/ejecutadas: ...
- No comprobado e incertidumbre: ...

La revisión es local; no se publicó ni constituye aprobación del PR.
```
