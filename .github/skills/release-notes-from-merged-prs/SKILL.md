---
name: release-notes-from-merged-prs
description: 'Redacta notas de versión trazables a PR integrados entre dos referencias Git. Usa cuando se soliciten release notes, notas de versión o changelog basado en PR; resuelve referencias mediante GitHub MCP y no publica releases.'
argument-hint: '[repositorio] [referencia inicial] [referencia final]'
---

# Notas de versión desde PR integrados

Produce un archivo local de notas de versión para un intervalo de un repositorio. La inclusión exige evidencia de que cada PR se integró dentro del intervalo; un PR abierto, cerrado sin integrar o meramente mencionado no basta. No publiques una release, no crees tags y no hagas cambios remotos.

## Procedimiento

1. **Identifica el repositorio y las referencias.**
   - Usa el repositorio indicado por la persona. Si no se especifica, identifica el repositorio actual a partir de su remoto Git.
   - Usa las referencias inicial y final solicitadas. Si no se especifican, elige referencias explícitas que acoten cambios útiles (por ejemplo, dos tags, o el SHA base previo al cambio y la rama final). Explica la selección.
   - Busca y utiliza herramientas GitHub MCP para listar ramas/tags y consultar commits. Resuelve cada referencia con MCP a su SHA completo; no uses nombres de rama mutables como sustituto del SHA en las notas.
   - Verifica que el inicio sea ancestro del final y define el intervalo como `(SHA inicial, SHA final]`. Si no puedes establecer la relación, no presentes el conjunto como completo: informa el bloqueo o incertidumbre.

2. **Busca PR candidatos y demuestra su integración en el intervalo.**
   - Consulta los PR del repositorio con una búsqueda de PR integrados (`is:merged` o filtro equivalente), paginando hasta cubrir los resultados pertinentes. No deduzcas integración únicamente de `state: closed`, de una fecha, del título, de commits mencionados en documentación o de que la rama siga existiendo.
   - Para cada candidato, consulta los detalles del PR y los commits de la rama final mediante MCP. Comprueba el indicador de integración y encuentra el commit de integración (merge, squash o rebase) en el historial comprendido entre los dos SHA, excluyendo el inicial e incluyendo el final.
   - Cuando MCP no exponga el SHA de integración, establece el vínculo con evidencia inequívoca del historial (por ejemplo, el commit de merge que referencia el PR, o un commit de squash asociado al PR) y su pertenencia al intervalo. Si no puede demostrarse inequívocamente, excluye el PR y anota la incertidumbre en la sección de evidencia; no lo conviertas en un cambio incluido.
   - Revisa el cuerpo, los archivos y el diff del PR para entender el comportamiento entregado. Basa las notas solo en evidencia del propio PR y del código/diff asociado. No atribuyas a un PR contenido de otro PR.

3. **Escribe cambios y acciones justificadas.**
   - Resume el efecto observable con precisión y añade un enlace directo al PR.
   - Añade acciones para quien instala, configura o usa el producto solo si el PR demuestra que son necesarias (por ejemplo, una variable nueva, un formato de token requerido o un cambio explícito de contrato). Explica brevemente la justificación verificable; distingue configuración de despliegue de acciones del usuario final.
   - Si no hay acciones requeridas demostradas, indícalo expresamente o no añadas una acción. No inventes beneficios, métricas, correcciones, compatibilidad o incompatibilidades.
   - Mantén visibles limitaciones de validación o dependencias relevantes documentadas por el PR. No afirmes que se ejecutaron pruebas: atribúyelas al PR si solo constan allí.

4. **Entrega y verifica el archivo local.**
   - Crea o actualiza el archivo de notas pedido; si no se indicó una ruta, usa `RELEASE_NOTES.md` en la raíz del repositorio.
   - Incluye repositorio, referencias originales y SHA completos, definición del intervalo, cambios incluidos y evidencia/incertidumbres. Enlaza cada nota al PR.
   - Antes de terminar, verifica que cada nota tenga un PR con integración demostrada dentro del intervalo, que cada acción tenga justificación verificable y que las referencias/SHA correspondan a lo resuelto mediante MCP.
   - Si no se pudo demostrar una integración, exclúyela de las notas del producto y explica qué evidencia faltó. No rellenes vacíos con suposiciones.

## Formato sugerido

```markdown
# Notas de versión

Repositorio: `owner/repo`
Intervalo exclusivo/inclusivo: `ref inicial` (`SHA inicial`) → `ref final` (`SHA final`)

## Cambios

### [Área o efecto]
- Efecto: ...
- Acción requerida: ... (justificación en el PR) / Ninguna demostrada.
- PR: [#N — título](URL)

## Evidencia y límites
- Integración e inclusión/exclusión de PR, con evidencia MCP.
- Incertidumbres, pruebas no ejecutadas o límites que afectan al alcance.
```
