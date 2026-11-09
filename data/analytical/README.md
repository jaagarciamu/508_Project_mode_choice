# Productos analíticos locales

Esta capa contiene productos derivados que se regeneran desde la SQLite relacional y se excluyen de Git.

- `em2023_trip_dataset.csv`: una fila por viaje, con las columnas de `viajes` preservadas como se almacenan. `fexp_vj` se retiene como campo fuente y no se aplica en este archivo.
- `od_matrices/`: matrices de una versión anterior, limitadas al área interna del estudio y conservadas como registro histórico. El flujo vigente publica matrices diarias de cobertura observada completa en `outputs/matrices/`.

La estimación expandida vigente usa `fexp_hg` de `hogares`, aplicado a cada viaje del hogar mediante `key_hg`, de acuerdo con la fórmula de total de viajes descrita en Etapa IV. Las diferencias entre factores y entre productos se documentan; no se modifican valores fuente ni se fuerzan correspondencias geográficas.
