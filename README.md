# Mode Choice Bogotá — EM2023

Proyecto académico de CME 508 para estudiar la demanda observada de viajes en Bogotá y, posteriormente, la elección modal. El trabajo se desarrolla por niveles: **Level 0** establece la base de datos y su entendimiento; **Level 1** estudia la demanda observada y matrices origen-destino (OD); **Level 2** aborda la elección modal.

## Estado y alcance actual

El repositorio contiene fuentes locales EM2023 en `data/sources/raw/`. Esta carpeta y su estructura existente se conservan sin modificar. En particular, `data/sources/raw/Database/` contiene los CSV fuente. No se versionan ni se deben subir datos fuente o microdatos. Task 01 y el inventario de metadatos de Task 02 están establecidos. El inventario no lee filas de microdatos ni realiza auditoría de calidad, uniones, matrices OD o modelos.

## Requisitos y entorno (Windows)

Se usa Python 3.12 y [uv](https://docs.astral.sh/uv/). Desde Git Bash, en la raíz del repositorio:

```bash
uv python install 3.12
uv sync --extra source-docs
uv run python -m ipykernel install --user --name mode-choice-bogota --display-name "Python (Mode Choice Bogotá)"
uv run jupyter lab
```

`uv sync --extra source-docs` crea `.venv` e instala los lectores opcionales de Excel y PDF usados por el inventario de fuentes; las dependencias quedan fijadas en `uv.lock`. En VS Code, abrir la carpeta del proyecto, abrir un notebook, seleccionar **Select Kernel** y elegir **Python (Mode Choice Bogotá)** o el intérprete `.venv\Scripts\python.exe`. La instalación del kernel de usuario es opcional si VS Code detecta directamente `.venv`.

## Datos y gobernanza

- Mantener los archivos originales en `data/sources/raw/`; no renombrarlos, modificarlos ni moverlos.
- La ruta principal de las tablas es `data/sources/raw/Database/`. Los nombres y relaciones deben validarse con los propios datos y documentación.
- No subir datos fuente, microdatos ni derivados sensibles a Git. `.gitignore` excluye datos locales, pero no sustituye controles de acceso ni revisión antes de compartir.
- Los productos relacionales, intermedios y analíticos son distintos de las fuentes y deben documentar procedencia, transformaciones, unidad de observación y limitaciones.

## Arquitectura

- `notebooks/`: documentos de investigación ejecutables, con contexto, método, resultados y limitaciones.
- `src/mode_choice/`: lógica reutilizable solo cuando aporte valor.
- `sql/`: consultas reutilizables cuando SQL sea adecuado.
- `configs/`: configuración portable y relativa al proyecto; decisiones aún no validadas se marcan como pendientes.
- `data/relational/`, `data/interim/`, `data/analytical/`: capas locales derivadas; no contienen fuentes originales.
- `docs/`: decisiones, modelo, diccionario y metodología.

## Orden de notebooks

1. `00_project_setup.ipynb` — verificar raíz y configuración, sin leer microdatos.
2. `01_source_inventory.ipynb` — inventariar fuentes y documentación.
3. `02_data_quality_audit.ipynb` — revisar calidad y posibles claves.
4. `03_relational_model.ipynb` — validar relaciones y cardinalidades.
5. `04_cleaning_and_standardization.ipynb` — documentar y aplicar transformaciones aprobadas.
6. `05_relational_data_layer.ipynb` — construir la capa relacional validada.
7. `06_analytical_dataset_design.ipynb` — definir conjuntos por pregunta de investigación.

El notebook 01 genera el catálogo y esquema preliminar; las definiciones de columnas, claves, cardinalidades y tipos observados siguen pendientes de validación. Los notebooks 02–06 requieren los pasos empíricos anteriores antes de producir resultados. La etapa posterior Level 1 empieza con `10_od_matrix.ipynb`; Level 2 con `20_mode_choice_dataset.ipynb`.

## Reproducibilidad y siguientes pasos

Usar rutas relativas desde la raíz del repo, registrar dependencias en `pyproject.toml` y mantener `uv.lock` actualizado con `uv lock`/`uv sync`. Registrar decisiones en `docs/decisions/decision_log.md`; no inferir relaciones, mapeos geográficos, categorías modales ni reglas de expansión sin evidencia.

Siguiente tarea: **Task 03 — Data Quality Audit & Key Validation**, comenzando con el notebook `02_data_quality_audit.ipynb` y los esquemas preliminares generados por Task 02.
