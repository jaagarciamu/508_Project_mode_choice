# Auditoría de datos para elección modal

## Alcance

Auditoría descriptiva de la SQLite relacional local en modo solo lectura. La unidad candidata para una futura base analítica es el viaje (`viajes`); esta etapa no construye esa base, no decide inclusión final de variables y no estima modelos. Los campos fuente se conservan sin recodificación. Las definiciones no encontradas en la documentación disponible quedan pendientes, no se infieren a partir del nombre.

## Tamaño y relaciones candidatas

Conteos observados: `viajes` 100,174, `personas` 67,556, `hogares` 22,755, `vehiculos` 17,392, `etapas` 110,881.

El enlace candidato viaje–persona por `viajes.key_pers = personas.key_persona` empareja 100,174 filas de viaje; left_rows=100174; unmatched_left_rows=0; left_repeated_key_groups=45663; right_duplicate_key_groups=0; right_rows=67556. El enlace viaje–hogar por `key_hg` empareja 100,174; left_rows=100174; unmatched_left_rows=0; left_repeated_key_groups=20917; right_duplicate_key_groups=0; right_rows=22755. La clave alternativa `key_pers_viaja` se reporta solo como diagnóstico y no se usa como fallback.

Hay 0 viajes sin registro de etapa y 9,492 viajes con más de una etapa. Por tanto, los campos de etapa no deben unirse directamente sin agregación: eso multiplicaría viajes. Costos, pagos, tiempos y modos por etapa se perfilan a nivel de tabla etapa, pero esta auditoría no los suma al viaje.

## Perfil de campos y discrepancias

El diccionario `docs/data_dictionary/mode_choice_trip_dataset_fields.csv` contiene una fila por campo de las cinco tablas: tipo declarado, cobertura, valores categóricos con frecuencia cuando la cardinalidad es baja, estadísticas numéricas, definición documentada (si está disponible) y uso/transformación candidatos aún no aprobados. Para campos con más de 50 valores distintos no se enumeran los valores individuales; se reportan cardinalidad, faltantes y rango/resumen numérico cuando aplica.

Las comparaciones de atributos repetidos entre viaje, persona y hogar se encuentran en `outputs/tables/mode_choice_duplicate_field_comparison.csv`. Las diferencias son conteos de registros no coincidentes; no seleccionan una tabla como verdad ni cambian datos.

## Productos y siguiente paso

Los reportes agregados son `outputs/tables/mode_choice_relation_audit.csv`, `mode_choice_field_profile.csv` y `mode_choice_duplicate_field_comparison.csv`. No contienen identificadores ni filas de microdatos. La siguiente fase, después de revisar estos resultados, puede especificar y construir una base de una fila por viaje, definiendo de forma explícita cómo agregar atributos de hogar, vehículos y etapas. No se asume que estén disponibles atributos de alternativas no elegidas; por ello, el modo observado permite empezar con análisis descriptivo/asociativo, pero no basta por sí solo para establecer una comparación completa entre opciones.
