# Revisión de fuentes EM2023 y decisiones de uso

**Estado:** revisión documental de Etapa IV incorporada; el campo por campo y la reproducción de los scripts contractuales siguen fuera del alcance.
**Datos observados:** CSV locales EM2023 en `data/sources/raw/Database/`, conservados sin modificar.
**Jerarquía:** los documentos técnicos oficiales EM2023 definen la encuesta; los entregables del contrato 2022-1972 documentan procesos y resultados. El código de análisis contractual no se presupone disponible.

## Hallazgos de Etapa IV

- **P4 — validación y georreferenciación EODH:** el informe describe la aplicación de criterios MIC a 23.082 encuestas; 22.755 hogares quedaron válidos, 187 incompletos y 140 anulados. La base final ya pasó el proceso de validación y edición documentado; este proyecto no intenta reconstruir MIC sin formularios, mallas y registros originales.
- P4 reporta 56.240 registros en el producto georreferenciado y una base final de 100.174 viajes. La diferencia se conserva como discrepancia entre productos; el subconjunto georreferenciado no se usa como filtro ni como universo de la matriz.
- **P5 — bases finales EODH:** documenta 22.755 hogares, 67.556 personas, 48.539 personas con viajes, 100.174 viajes y 122.992 etapas. Describe la estructura hogar–personas/vehículos/viajes y viajes–etapas, y refiere una base final con y sin factores, diccionario y cuadros de salida.
- **P6 — expansión EODH:** el total de viajes por hogar se calcula con el factor de expansión del hogar multiplicado por los viajes reportados por ese hogar: `T = sum_h(fexp_hg * viajes_h)`. El informe reporta 16.723.044 viajes diarios, margen de error 446.648, CV 1,36% e intervalo 16.276.395–17.169.692.
- P6 también refiere rutinas R e insumos en un anexo. No se localizaron esos archivos entre los materiales locales catalogados, por lo que no se afirma reproducción exacta ni se bloquea una reconstrucción técnica con los campos disponibles.
- P6 página impresa 22 reporta 64.989 personas en el contexto de expansión; P4/P5 reportan 67.556 personas en la base final. La diferencia de denominador no está reconciliada en los archivos disponibles y no se usa para filtrar viajes.

## Factores de expansión: verificación empírica local

La SQLite local contiene `fexp_hg` en `hogares` y `fexp_vj` en `viajes`, relacionadas mediante `key_hg`. En los 100.174 viajes, ambos campos son no vacíos, numéricos y positivos; cada uno es constante dentro de los 21.508 hogares con viajes. Sin embargo, no coinciden en 90.194 filas. Sus sumas repetidas por registro de viaje son 16.723.042,90 para `fexp_hg` y 16.723.043,30 para `fexp_vj`.

El pipeline usa `fexp_hg` por viaje porque coincide con la fórmula de total de viajes por hogar descrita en P6. `fexp_vj` se conserva y se reporta como contraste. La diferencia registro a registro permanece visible; la cercanía de ambos totales al benchmark no demuestra que los factores sean intercambiables, que su derivación sea igual ni que el procedimiento oficial se haya replicado. No se altera ni recalibra ningún factor.

## Geografía y códigos de zona

La matriz usa los campos originales `zat_ori` y `zat_des` como texto; solo los valores nulos o vacíos impiden asignar una celda. Se conservan los demás códigos tal como aparecen, incluidos los que no tengan clasificación confirmada, y no se crea una equivalencia con UTAM, ZAT de otro año, municipio u otra geografía.

En el DBF ZAT2023 los códigos se leen como números decimales, mientras que los códigos de viaje son cadenas de texto (por ejemplo, la representación numérica del DBF incluye `.0`). Como la unión exigiría coerción de representación y no se dispone de una regla oficial de crosswalk para este producto, la geografía no filtra ni renombra zonas. Las diferencias de representación y códigos no clasificados se documentan en QA.

La versión OD anterior aplicaba una clasificación geográfica y contaba 99.741 viajes internos, incluidos 15.013 intrazonales. El flujo vigente incluye los 433 registros restantes usando sus códigos originales y cuenta 15.016 intrazonales en el universo ampliado. Los tres intrazonales adicionales están fuera del universo interno anterior. Estas cifras describen el cambio de alcance, no una corrección de los datos.

## Producto vigente de matrices OD

`notebooks/02_daily_od_matrices.ipynb` genera una matriz diaria muestral y una matriz expandida reconstruida técnicamente, ambas dispersas en formato largo. La unidad muestral es el registro de viaje; se incluye cada fila con origen y destino no vacíos, se conserva la intrazonalidad y no se aplican filtros por modo, propósito, edad u otros atributos. No se producen matrices por modo ni períodos AM/PM.

La matriz expandida repite `fexp_hg` del hogar para cada viaje asociado. Las celdas conservan el mismo conjunto de pares OD de la muestra. Si para una celda no hay cobertura completa de factor válido, su estimación queda vacía y la pérdida de cobertura aparece en los reportes, no como cero.

El benchmark de 16.723.044 se usa solo como contraste descriptivo. La matriz expandida local suma 16.723.042,90 (diferencia -1,10; aproximadamente -0,0000066%). No se fuerza concordancia ni se interpreta como éxito de reproducción. No se estiman errores estándar, intervalos o CV por celda; el CV publicado del total no se aplica a celdas OD.

Las fuentes EODI, sus factores, aforos y metodología de Etapa V son líneas distintas y no se usan para ajustar el producto EODH.
