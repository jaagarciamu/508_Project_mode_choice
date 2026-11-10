# Mode Choice Bogotá — EM2023

Proyecto académico de CME 508 sobre la demanda observada de viajes en Bogotá y la elección modal. El flujo usa las fuentes locales EM2023 y produce bases consolidadas y productos analíticos reproducibles. El objetivo principal es estudiar la elección modal; las matrices diarias OD son una etapa descriptiva intermedia.

## Estado del proyecto

- **Level 0 — bases y auditoría:** el inventario de fuentes, el diccionario, las auditorías agregadas, la SQLite relacional y el dataset de viajes están disponibles localmente. Las fuentes originales no se modifican ni se versionan.
- **Level 1 — matrices OD:** se generan una matriz diaria muestral y una expandida técnicamente con el factor de hogar `fexp_hg`, siguiendo la forma documentada en Etapa IV de sumar el factor del hogar por cada viaje reportado. `fexp_vj` se conserva como contraste porque difiere del factor del hogar en 90.194 de 100.174 registros.
- La matriz actual incluye los 100.174 viajes con origen y destino no vacíos, códigos originales y viajes intrazonales. La versión histórica limitada al área interna incluía 99.741 viajes y 15.013 intrazonales; la versión ampliada incluye 433 registros adicionales y 15.016 intrazonales.
- El total expandido local con `fexp_hg` es 16.723.042,90, una diferencia de -1,10 respecto al total publicado de 16.723.044. Esta proximidad es solo un contraste descriptivo: no valida equivalencia de factores, universos o procedimientos ni constituye reproducción oficial.
- No se normalizan códigos para forzar emparejamientos geográficos. Los códigos quedan como texto original; las referencias que no coinciden exactamente se documentan como no clasificadas y permanecen en las matrices.
- No se calculan medidas de incertidumbre por celda, matrices por modo ni matrices AM/PM. Esas decisiones exceden el producto OD diario actual.
- **Level 2 — auditoría para elección modal:** se perfilarán relaciones, cobertura, variables y categorías de las cinco tablas antes de construir una base enriquecida por viaje. No se imputan alternativas no observadas ni se estiman modelos en esta etapa.

## Entorno (Windows)

Se usa Python 3.12 y [uv](https://docs.astral.sh/uv/). Desde la raíz del repositorio:

```bash
uv python install 3.12
uv sync --extra source-docs --extra geospatial
uv run python -m ipykernel install --user --name mode-choice-bogota --display-name "Python (Mode Choice Bogotá)"
uv run jupyter lab
```

`uv.lock` fija las dependencias, incluido `pyarrow` para los productos Parquet. En VS Code se puede elegir el kernel **Python (Mode Choice Bogotá)** o `.venv\Scripts\python.exe`.

## Flujo principal

1. `notebooks/01_data_audit.ipynb` — refrescar el inventario y ejecutar auditorías agregadas; inspeccionar la base relacional existente en solo lectura. No reconstruye la SQLite.
2. `notebooks/02_daily_od_matrices.ipynb` — generar matrices diarias muestral y expandida, conciliación, QA, resumen por zona e informe metodológico.
3. `notebooks/03_mode_choice_data_audit.ipynb` — auditoría de relaciones, perfiles de campos y categorías; produce un diccionario analítico y reportes agregados. No construye todavía la base enriquecida.
4. `notebooks/04_mode_choice_join_preview.ipynb` — genera `data/interim/mode_choice_trip_join_preview_350.csv`, muestra local de 350 viajes proporcional por modo para revisar la unión persona/hogar y distancia entre centroides ZAT; resúmenes de vehículos/etapas siguen exploratorios.
5. `notebooks/05_mode_choice_analysis.ipynb` — fase futura para consolidar la base analítica por viaje y desarrollar el análisis modal, una vez acordadas las reglas de agregación y alcance.

Los notebooks previos se conservan en `notebooks/archive/` como registro de análisis y no forman parte del flujo principal vigente.

## Bases y productos

- `data/relational/em2023_relational.sqlite`: cinco tablas fuente consolidadas y relaciones validadas. Es una base local y está excluida de Git.
- `data/analytical/em2023_trip_dataset.csv`: una fila por viaje, con los campos de `viajes` preservados tal como se almacenan; `fexp_vj` se conserva sin aplicar.
- `data/interim/mode_choice_trip_join_preview_350.csv`: muestra local de revisión de 350 viajes con microdatos e identificadores; excluida de Git y no apta para publicación. El CSV sin sufijo `_350` es la muestra histórica de 33 viajes.
- `outputs/matrices/`: matrices OD diaria en CSV y Parquet, dispersas y en formato largo.
- `outputs/tables/`: conciliación, calidad de datos y resumen de zonas.
- `outputs/reports/`: metodología, supuestos y limitaciones.
- `docs/data_dictionary/mode_choice_trip_dataset_fields.csv`: diccionario de campos de las tablas relacionales, definiciones pendientes y perfiles observados.

Los productos generados locales se excluyen de Git por defecto. Los agregados no contienen identificadores de viaje, hogar o persona.

## Reglas de datos y metodología

- Mantener los archivos originales en `data/sources/raw/` sin renombrarlos, modificarlos ni moverlos.
- Usar `viajes` como unidad de conteo para la matriz muestral. Incluir todo registro con códigos OD no vacíos, sin filtros por modo, propósito u otros atributos; retener intrazonales.
- Para la estimación expandida, repetir el `fexp_hg` del hogar por cada viaje asociado mediante `key_hg`, equivalente a sumar por hogar el factor multiplicado por sus viajes. `fexp_vj` se reporta como diagnóstico comparativo.
- Mantener los códigos de zona sin recodificar. La geografía disponible puede usarse como referencia descriptiva únicamente donde la correspondencia sea verificable; no se descartan zonas por falta de correspondencia.
- Reportar factores inválidos, registros sin códigos OD, diferencias frente a cifras publicadas y limitaciones. No ajustar pesos ni códigos para forzar acuerdos.
- Los resultados se describen como matriz muestral y estimación expandida reconstruida técnicamente; no se afirma reproducción exacta del método oficial.

## Documentación y trazabilidad

`docs/data_dictionary/` contiene catálogos, esquemas y auditorías agregadas. `docs/data_dictionary/source_review.md` resume la revisión de fuentes EODH/EODI. `docs/decisions/decision_log.md` registra las decisiones de alcance, expansión, geografía y limitaciones. Revisar `git status` antes de compartir el repositorio para asegurar que no se incluyan microdatos o productos locales.
