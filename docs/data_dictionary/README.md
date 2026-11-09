# Diccionario, catálogo y auditoría de datos

Los archivos de este directorio registran nombres y estructuras de las fuentes, definiciones documentadas, características observadas, relaciones empíricas y limitaciones. No se infieren significados de variables ni se corrigen datos fuente.

`notebooks/01_data_audit.ipynb` regenera el inventario y esquema a partir de la estructura de `data/sources/raw/`, las auditorías agregadas de calidad y los reportes de validación de claves/relaciones. También verifica la SQLite existente en modo de solo lectura; no reconstruye la base.

`notebooks/02_daily_od_matrices.ipynb` genera las matrices diarias y reportes de Level 1. Los registros OD con códigos no vacíos se cuentan usando los valores de zona fuente sin normalizarlos. Los códigos sin clasificación geográfica permanecen en la matriz.

`notebooks/03_mode_choice_data_audit.ipynb` valida relaciones y cobertura de las cinco tablas relacionales y genera perfiles y un diccionario separado para la preparación de elección modal. El diccionario lista categorías con frecuencias para campos de baja cardinalidad; en campos de alta cardinalidad conserva el resumen. Las definiciones permanecen pendientes cuando no se localizaron en la documentación. La auditoría no construye todavía una base enriquecida ni agrega campos de etapas al viaje.

`notebooks/04_mode_choice_join_preview.ipynb` genera una muestra local de hasta tres viajes por modo observado para inspeccionar cómo se unen persona y hogar y cómo se podrían resumir las relaciones uno a muchos. La muestra contiene microdatos e identificadores, está excluida de Git y no es representativa. Los agregados exploratorios de etapas y vehículos no son reglas finales para la base de modelado.

`source_review.md`, `eodh_methodology_evidence.csv` y `eodh_matrix_open_decisions.csv` resumen la evidencia de Etapa IV, las decisiones operativas y las limitaciones no bloqueantes. Los informes de Etapa IV son evidencia metodológica contextual; las bases de datos entregadas son la fuente de valores observados.

Los notebooks previos a este flujo se preservan bajo `notebooks/archive/` como referencia histórica. Los informes CSV contienen métricas agregadas y no valores de microdatos ni identificadores individuales.
