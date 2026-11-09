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

## DEC-006 — Universo de matrices diarias EODH

- **Fecha:** 2026-11-09
- **Tema:** inclusión de viajes para la matriz descriptiva diaria
- **Decisión:** contar cada registro de `viajes` una vez cuando sus identificadores originales de origen y destino no estén vacíos; conservar intrazonales y no filtrar por modo, propósito ni atributos personales.
- **Justificación:** la matriz es un producto descriptivo intermedio. La base final ya pasó por la validación contractual documentada en Etapa IV; el proyecto no dispone de las capturas, mallas y scripts MIC para reconstruir el proceso.
- **Consecuencias:** cualquier viaje sin uno de los dos códigos se reporta en QA; todos los demás pares, incluidos los no clasificados geográficamente, permanecen en las tablas OD.
- **Evidencia/referencias:** `notebooks/02_daily_od_matrices.ipynb`; informes P4 y P5 de Etapa IV; `eodh_matrix_open_decisions.csv`.
- **Estado:** aceptada para el producto técnico.

## DEC-007 — Factor para la estimación expandida de viajes

- **Fecha:** 2026-11-09
- **Tema:** aplicación del factor de expansión en OD diario
- **Decisión:** usar el `fexp_hg` del hogar vinculado por `key_hg` para cada viaje. Esto implementa `sum_h(fexp_hg * viajes_h)`. Conservar `fexp_vj` como diagnóstico, no como peso principal.
- **Justificación:** el informe P6 de Etapa IV describe explícitamente el estimador de total de viajes a nivel hogar. En los datos locales ambos factores son completos, numéricos, positivos y constantes dentro del hogar, pero difieren en 90.194 de 100.174 viajes. Sus totales son cercanos al benchmark, lo que no prueba equivalencia de los factores.
- **Consecuencias:** denominar el resultado “estimación expandida reconstruida técnicamente”; no afirmar reproducción del código contractual ni ajustar pesos para forzar el benchmark. Si faltara un factor válido en una celda, su estimación quedará vacía y se reportará su cobertura incompleta.
- **Evidencia/referencias:** P6 páginas impresas 20–23; `eodh_methodology_evidence.csv`; `notebooks/02_daily_od_matrices.ipynb`.
- **Estado:** aceptada para el producto técnico.

## DEC-008 — Identificadores de zona y geografía de referencia

- **Fecha:** 2026-11-09
- **Tema:** preservación de códigos OD
- **Decisión:** conservar `zat_ori` y `zat_des` literalmente como texto fuente. No normalizar representaciones, asignar zonas por inferencia ni restringir matrices por municipio. Las referencias geográficas no resueltas se reportan como no clasificadas.
- **Justificación:** los campos fuente son texto y el DBF ZAT2023 presenta valores numéricos decimales; no se adopta una regla contractual que autorice coerción o crosswalk para este producto.
- **Consecuencias:** los 433 registros previamente excluidos por el ámbito interno se incluyen con sus códigos originales. Se informa su diferencia con el producto histórico sin asignarles una nueva clasificación.
- **Evidencia/referencias:** esquema y datos locales, `source_review.md`, `notebooks/02_daily_od_matrices.ipynb`.
- **Estado:** aceptada para el producto técnico.

## DEC-009 — Incertidumbre y benchmark

- **Fecha:** 2026-11-09
- **Tema:** interpretación estadística de matrices OD
- **Decisión:** publicar conteos muestrales y sumas expandidas; comparar con 16.723.044 usando diferencias absoluta y porcentual. No calcular incertidumbre por celda ni forzar concordancia.
- **Justificación:** el CV del total publicado no permite inferir incertidumbre de celdas OD, y no se dispone del procedimiento de varianza/repeticiones de los scripts contractuales.
- **Consecuencias:** diferencia frente al benchmark es descriptiva, no criterio de éxito. No se publican matrices por modo ni AM/PM en esta fase.
- **Evidencia/referencias:** P6 de Etapa IV; `eodh_matrix_open_decisions.csv`; reporte de metodología OD.
- **Estado:** aceptada.

## DEC-010 — Organización del flujo reproducible

- **Fecha:** 2026-11-09
- **Tema:** consolidación de notebooks y productos
- **Decisión:** usar `01_data_audit.ipynb` y `02_daily_od_matrices.ipynb` como flujos activos actuales; reservar `03_mode_choice_analysis.ipynb` para la fase siguiente. Preservar los notebooks anteriores en `notebooks/archive/`.
- **Justificación:** reducir el flujo activo sin descartar el trabajo previo ni reconstruir bases ya consolidadas.
- **Consecuencias:** `01_data_audit` refresca inventarios/auditorías agregadas y verifica la SQLite en solo lectura; `02_daily_od_matrices` genera productos y QA. Los datos fuente y las bases locales permanecen intactos.
- **Estado:** aceptada.

## Seguimientos documentales no bloqueantes

- Recuperar, si se obtiene acceso, los anexos de rutinas R citados en P6 para comparar la reconstrucción con el procedimiento contractual. Su ausencia no detiene el producto técnico.
- Aclarar la diferencia entre 64.989 personas reportadas en P6 durante la expansión y 67.556 en P4/P5 como total de la base final; no se aplica como filtro de viajes.
- Documentar una geografía ZAT/crosswalk si se obtiene la versión oficial que vincule sin ambigüedad los códigos de origen/destino con zonas y cobertura. Hasta entonces los códigos se conservan sin clasificación.
