# Registro de decisiones

## DEC-001 — Estructura y protección de fuentes

- **Fecha:** 2026-11-01
- **Tema:** estructura del repositorio y gobernanza de fuentes
- **Decisión/estado:** Aceptada. Preservar `data/sources/raw/` y su contenido en su ubicación actual; mantener los datos locales y excluidos de Git.
- **Justificación:** las fuentes EM2023 ya están suministradas en el repositorio y son la base empírica del proyecto.
- **Alternativas consideradas:** mover o renombrar fuentes; versionar microdatos.
- **Consecuencias:** nuevos productos derivados van en capas separadas; revisar `git status` antes de cualquier publicación.
- **Evidencia/referencias:** inspección del árbol del repositorio y decisión del investigador.
- **Estado:** aceptada.

## DEC-002 — Entorno reproducible

- **Fecha:** 2026-11-01
- **Tema:** Python y gestión de dependencias
- **Decisión/estado:** Aceptada. Usar Python 3.12, `uv`, `pyproject.toml`, `uv.lock` y `.venv` local ignorado por Git.
- **Justificación:** reproducibilidad local en Windows y control explícito de dependencias.
- **Alternativas consideradas:** instalar dependencias globalmente o usar otro gestor.
- **Consecuencias:** sincronizar con `uv sync`; mantener el lockfile en Git.
- **Evidencia/referencias:** especificación del proyecto.
- **Estado:** aceptada.

## DEC-003 — Dependencias iniciales

- **Fecha:** 2026-11-01
- **Tema:** entorno mínimo de notebooks
- **Decisión/estado:** Aceptada. Incluir JupyterLab, ipykernel, pandas y PyYAML. Posponer DuckDB, Parquet, herramientas geoespaciales y modelado hasta justificar su uso.
- **Justificación:** habilitar configuración, notebooks y análisis tabular sin imponer infraestructura prematura.
- **Alternativas consideradas:** incluir de antemano todos los candidatos tecnológicos.
- **Consecuencias:** añadir paquetes en etapas posteriores y actualizar el lockfile.
- **Evidencia/referencias:** alcance de Task 01.
- **Estado:** aceptada.

## DEC-004 — Jerarquía de documentos EM2023 y contrato

- **Fecha:** 2026-11-01
- **Tema:** uso de documentación fuente
- **Decisión/estado:** Aceptada. La documentación oficial EM2023 define la encuesta; los informes del contrato 2022-1972 se conservan como referencias contextuales.
- **Justificación:** separar definiciones empíricas del instrumento de encuesta de productos metodológicos del contrato.
- **Alternativas consideradas:** tratar ambos grupos documentales como fuentes equivalentes.
- **Consecuencias:** una definición de variable debe citar documentación EM2023 explícita; los informes de contrato pueden orientar etapas posteriores, como matrices OD.
- **Evidencia/referencias:** confirmación del investigador y revisión inicial de títulos y secciones.
- **Estado:** aceptada.

## DEC-005 — Lectura opcional de documentos fuente

- **Fecha:** 2026-11-01
- **Tema:** formatos auxiliares para Task 02
- **Decisión/estado:** Aceptada. Añadir `openpyxl` y `pypdf` al extra opcional `source-docs` para leer metadatos de libros y PDFs sin hacerlos dependencias obligatorias del entorno base.
- **Justificación:** reproducir el catálogo documental manteniendo ligera la instalación base.
- **Alternativas consideradas:** depender solo de herramientas GUI o añadir parsers al entorno base.
- **Consecuencias:** ejecutar `uv sync --extra source-docs` antes del notebook 01.
- **Evidencia/referencias:** formatos existentes en el árbol local de fuentes.
- **Estado:** aceptada.

## Decisiones metodológicas pendientes

- Claves primarias y foráneas, cardinalidades y unidad de observación de tablas.
- Mapeos de modos, geografía ZAT y cobertura territorial.
- Uso y universo válido de factores de expansión.
- Formato de almacenamiento de capas derivadas y motor SQL, si se necesitan.
