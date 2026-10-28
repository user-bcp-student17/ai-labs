---
name: pr-review-orchestrator
description: 'Orquesta una revisión acotada de PR. Pregunta si se revisarán pruebas, seguridad o compatibilidad, luego aplica solo el Skill elegido y produce un informe local sustentado por el diff y SHAs obtenidos mediante GitHub MCP.'
argument-hint: '[owner/repo] [número de PR]'
---

# Orquestador de revisión de PR

Coordina una sola revisión especializada. Este Skill no sustituye los de pruebas, seguridad o compatibilidad ni ejecuta los tres aspectos juntos.

## Selección del aspecto

1. Detecta si la persona ya eligió claramente uno de estos aspectos:
   - **Pruebas** — suficiencia y relevancia de las pruebas para los cambios.
   - **Seguridad** — defectos o riesgos de seguridad en el diff.
   - **Compatibilidad** — preservación de contratos y consumidores existentes.
2. Si no eligió, pregúntale qué aspecto quiere revisar antes de consultar el PR. Usa una pregunta estructurada con estas tres opciones si la herramienta de preguntas está disponible; si no, pregunta en el chat y espera respuesta. No infieras la selección a partir del contenido del PR.
3. Si selecciona más de un aspecto, pide que elija uno para esta ejecución. No mezcles alcances.

## Enrutamiento

Una vez elegido el aspecto, lee y sigue el procedimiento completo del Skill correspondiente:

- Pruebas → [pr-testing-review](../pr-testing-review/SKILL.md)
- Seguridad → [pr-security-review](../pr-security-review/SKILL.md)
- Compatibilidad → [pr-compatibility-review](../pr-compatibility-review/SKILL.md)

No inventes que otro Skill fue cargado o ejecutado: aplica explícitamente sus instrucciones y conserva su criterio, clasificación, evidencia y formato.

## Coordinación común

- Recibe `owner/repo` y número del PR de los argumentos/contexto. Si falta información y el PR no es inequívoco, pide aclaración.
- El Skill especializado debe consultar los detalles y el diff con GitHub MCP y fijar los SHA completos de base y cabeza. No uses MCP para publicar comentarios o reviews.
- Si el servidor MCP o sus herramientas de lectura no están disponibles, informa el bloqueo y no finjas una consulta; pide habilitar acceso o proporcionar evidencia versionada suficiente.
- Entrega únicamente el informe local indicado por el Skill elegido. No edites el PR, no publiques resultados, no apruebes y no presentes la revisión como aprobación.
- Informa qué aspecto se eligió, qué archivo local se generó y qué pruebas/contextos se inspeccionaron o ejecutaron realmente.
