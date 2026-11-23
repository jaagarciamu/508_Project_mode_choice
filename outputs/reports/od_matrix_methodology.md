# Matrices diarias OD EODH — metodología y limitaciones

## Productos y fuente

Las matrices son productos descriptivos del archivo local `data/relational/em2023_relational.sqlite`, usando las tablas `viajes` y `hogares`. La base se abre en modo de solo lectura. La tabla de viajes conserva 100,174 registros y la clave `key_viaje` es única y no nula.

Se incluyen todos los registros con códigos de origen y destino no vacíos, sin filtros por propósito, modo, edad, tiempo u otras características. Los identificadores de zona se conservan como texto exactamente como están almacenados. Los códigos vacíos se contabilizan en QA y no forman una celda OD. Se retienen los intrazonales y todos los pares observados, incluso cuando el código no tenga una correspondencia geográfica validada.

El CSV y Parquet se publican en formato disperso largo: una fila por par observado, columnas `zat_ori`, `zat_des` y conteo o expansión. Los pares de la matriz expandida siguen la misma lista que la matriz muestral. Cuando algún viaje del par carezca de un factor válido, la expansión de esa celda queda vacía y se informa su cobertura; no se representa como cero.

## Regla de expansión

El informe P6 de Etapa IV describe el total de viajes mediante la suma por hogar del factor de expansión del hogar multiplicado por el número de viajes reportados por ese hogar. Se aplica la forma equivalente de repetir `fexp_hg` en cada viaje asociado: suma de factores de hogar por registro de viaje. Es una reconstrucción técnica basada en la fórmula documentada, no una reproducción exacta de los scripts contractuales.

En los datos actuales, `fexp_hg` es numérico en 100,174 viajes, de los cuales 100,174 tienen valor positivo; su suma repetida por viaje es 16.723.042,90. El campo `fexp_vj` es numérico en 100,174 viajes, de los cuales 100,174 tienen valor positivo; su suma es 16.723.043,3. `fexp_hg` varía dentro de 0 hogares con viajes y `fexp_vj` dentro de 0; ambos factores difieren en 90,194 registros. `fexp_vj` se reporta como diagnóstico, no se usa como peso principal.

## Geografía y cobertura

No se asigna municipio, pertenencia al área de estudio ni equivalencia espacial a partir de una conversión inferida de códigos. En la revisión local, los identificadores fuente son texto y el campo ZAT del DBF de referencia se almacena como número decimal; no hay coincidencias de representación exacta. Por esa razón el DBF no se usa para filtrar ni para renombrar zonas. Los posibles códigos no emparejados quedan incluidos en las matrices y aparecen en el resumen por zona como sin clasificación geográfica validada.

El producto georreferenciado de Etapa IV reporta 56.240 registros frente a los 100.174 viajes de la base final. Se trata como diferencia descriptiva entre productos; no se usa como universo o filtro de las matrices. El informe de validación documenta 23.082 hogares encuestados, 22.755 válidos tras MIC, 187 incompletos y 140 anulados. Este pipeline usa la base final ya procesada y no intenta reconstruir el MIC.

La matriz histórica restringida al área de estudio contenía 99.741 viajes y 15.013 intrazonales. La matriz actual incorpora los 433 registros restantes con sus códigos originales y registra 15.016 intrazonales en el universo ampliado; los tres casos adicionales provienen de fuera de la matriz histórica restringida.

## Conciliación con el benchmark

El total expandido con cobertura de factor completa es 16.723.042,90. Frente al benchmark publicado de 16.723.044, la diferencia es -1,10 (-0,0000066% del benchmark). Esta comparación es descriptiva: la proximidad no valida la equivalencia de factores, universos, geografía o procedimientos.

## Limitaciones

- No se reconstruyen las rutinas R contractuales citadas en el anexo del informe P6, que no están presentes entre los archivos locales catalogados.
- El campo `fexp_vj` no coincide registro a registro con `fexp_hg`; no se interpreta esa discrepancia como error ni se corrigen los valores.
- No se calculan errores estándar, intervalos de confianza o CV por celda. El CV publicado para el total no se aplica a las celdas OD.
- No se generan matrices por modo ni por período AM/PM, y no se usan factores EODI ni aforos.
- Diferencias en completitud, geografía o denominadores se documentan como limitaciones, sin forzar coincidencias con el producto publicado.

## Trazabilidad

La evidencia está en los informes P4, P5 y P6 de Etapa IV, el inventario de fuentes y `docs/decisions/decision_log.md`. Los productos agregados no incluyen identificadores de viaje, hogar o persona.
