---
name: source-diagram-generator
description: Transforma fragmentos de código, pseudocódigo o lógica de negocio en diagramas de flujo y arquitectura estructurados, exportándolos directamente a formato PNG para su documentación inmediata.
---

# Skill: Source Diagram Generator

## 1) Metadata
- **Skill ID:** source-diagram-generator
- **Version:** 0.1.0
- **Purpose:** Automatizar la creación de diagramas técnicos (flujos, arquitectura, secuencia) a partir de código o lógica estructurada, entregando una representación visual limpia en formato PNG y su código fuente correspondiente.
- **Audience (roles):** Tech Lead, Software Architect, Backend, Frontend, QA, Devops
- **When to use:** Al documentar una funcionalidad existente, diseñar la arquitectura de un nuevo módulo o explicar flujos lógicos complejos en un PR o wiki.
- **When NOT to use:** Para maquetación de interfaces de usuario (UI/UX), diagramas organizacionales no técnicos o cuando no se disponga de la lógica/sintaxis del proceso.
- **Sensitive inputs:** No incluyas credenciales, tokens, secretos, IP internas, variables de entorno reales ni lógica de negocio patentada o confidencial.
- **Expected output:** Una imagen PNG incrustada/generada del diagrama junto con el código fuente del gráfico (ej. Mermaid o PlantUML) en Markdown.

## 2) Inputs

Proporciona la información en este formato:
- Source code / Logic snippet: (El código fuente, pseudocódigo o descripción paso a paso)
- Diagram type: (Flujo, Secuencia, Arquitectura, Entidad-Relación)
- Target format: PNG
- Technical context: (Lenguaje de programación, stack tecnológico involucrado)
- Key entities/nodes to highlight: (Componentes, servicios o bases de datos críticas a mostrar)
- Flow direction: (Arriba-Abajo [TB], Izquierda-Derecha [LR])

## 3) Output

Devuelve solo un documento Markdown con estas secciones:
1. Visual Diagram (PNG)
	- [Renderizado o enlace directo a la imagen PNG generada del diagrama]
2. Diagram Source Code
	- Bloque de código con la sintaxis utilizada para generar el diagrama (Mermaid, PlantUML, etc.) para futura edición.
3. Flow Breakdown
	- Explicación concisa y numerada de los pasos secuenciales o interacciones representadas en el gráfico.
4. Key Components & Tech Stack
	- Listado de los nodos o capas principales identificadas (ej. API Gateway, DB, Microservicio) y su rol en el flujo.
5. Edge Cases & Exceptions Handled
	- Flujos alternativos o de error que fueron mapeados visualmente (ej. reintentos, capturas de error 500).
6. Open Questions / Ambiguities
	- Puntos del código de entrada que no quedaron claros o lógica difusa que requirió supuestos para ser graficada.

## 4) Constraints

- Los diagramas deben ser autocontenidos y autoexplicativos; cada nodo debe tener una etiqueta clara.
- No omitas flujos de error o caminos críticos si están explícitos en el código de entrada.
- El código fuente del diagrama generado debe ser estándar (compatible con renderizadores comunes de Markdown).
- El archivo de imagen PNG final debe configurarse con un fondo contrastante (blanco o transparente legible) apto para temas claros y oscuros.
- No asumas dependencias externas que no se mencionen o sugieran fuertemente en el input.

## 5) Validation Rules

La salida es válida si:
- Incluye el diagrama visual en formato PNG y su código fuente editable.
- El diagrama cuenta con una dirección de flujo clara (TB o LR) y no tiene bucles infinitos sin salida visual.
- Mapea correctamente al menos el camino feliz (happy path) y un camino de excepción/error (si aplica).
- El desglose secuencial (Flow Breakdown) coincide exactamente con los nodos y flechas del PNG.
- No expone datos sensibles ni cadenas de texto confidenciales del código original.

## 6) Evidence

Adjunta o referencia estos elementos en el repositorio o entrega de la skill:
- `SKILL.md` versionado.
- `examples/code-input.sample.md` (Código o lógica de ejemplo).
- `examples/diagram-output.sample.png` (Imagen PNG generada de prueba).
- `examples/diagram-source.sample.md` (Código fuente del gráfico de prueba).
- Tag de versión para el Skill, como `skill-source-diagram-generator-v0.1.0`.