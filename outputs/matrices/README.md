# Matrices OD

Matrices diarias EODH dispersas en formato largo. Cada fila representa un par OD observado; los códigos de zona se conservan como texto de la fuente. CSV y Parquet se regeneran con `notebooks/02_daily_od_matrices.ipynb` y los productos están excluidos de Git por defecto.

- `od_daily_sample`: conteo de viajes de la muestra.
- `od_daily_expanded`: estimación técnica con el factor de hogar documentado; celdas sin cobertura completa del factor quedan vacías.
