# Mode choice variable classification and final decisions

This table preserves the investigator-provided initial classification for the original 126 fields and records the final Tarea 03 decision and rationale. Documentation is in English; source names and values are not translated or recoded.

The 20 fields confirmed as exact copies are excluded. Fields explicitly excluded by the investigator remain excluded even when no direct comparison exists; those exclusions are not described as duplicates unless the matrix confirms exact equality. `nom_mun_ori` and `nom_mun_des` are included as original fields required for territorial harmonization. `estra_hg` remains unchanged, including the categorical value `No aplica`.

The derived time and territory fields are appended with their construction rules. Territory categories are `Localidad`, `Municipio`, and `No disponible`; original locality and municipality values remain unchanged.

```tsv
COLUMNA	TIPO	Possible research_role	Decision Base Inicial	Final Decision	Final Rationale
cod_hg	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
nom_mun_hg	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
cod_upl_hg	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
cod_utam_hg	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
zat_hg	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
estra_hg	viaje	core_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
cod_pers	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
cod_vj	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
orden_vj	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
otro_vj	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
zat_ori	viaje	geographic_segmentation	SI	INCLUDE	Included according to the investigator-provided initial classification.
utam_ori	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
upl_ori	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
localidad_ori	viaje	geographic_segmentation	SI	INCLUDE	Included according to the investigator-provided initial classification.
nom_mun_ori	viaje	No_Inicially	NO	INCLUDE	Included as the original municipality field required for territorial harmonization in Tarea 03.
zat_des	viaje	geographic_segmentation	SI	INCLUDE	Included according to the investigator-provided initial classification.
utam_des	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
upl_des	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
localidad_des	viaje	geographic_segmentation	SI	INCLUDE	Included according to the investigator-provided initial classification.
nom_mun_des	viaje	No_Inicially	NO	INCLUDE	Included as the original municipality field required for territorial harmonization in Tarea 03.
hora_ini	viaje	core_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
hora_fin	viaje	extended_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
duracion_min	viaje	core_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
t_acceso_min	viaje	extended_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
t_espera_min	viaje	extended_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
t_egreso_min	viaje	extended_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
modo_principal_agrupado	viaje	target	SI	INCLUDE	Included according to the investigator-provided initial classification.
modo_principal_desagrupado	viaje	target	SI	INCLUDE	Included according to the investigator-provided initial classification.
motivo_viaje	viaje	core_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
motivo_viaje_cuidado	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
frecuencia_viaje	viaje	extended_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
etapas	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
app_antes_vj	viaje	extended_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
app_durante_vj	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
edad	viaje	core_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
sexo	viaje	core_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
genero	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
orien_sexual	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
identidad_etnica	viaje	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
madre_cab_familia	viaje	extended_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
max_nivel_edu	viaje	core_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
ocupacion_principal	viaje	core_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
key_hg	viaje	identifier	SI	INCLUDE	Included according to the investigator-provided initial classification.
key_pers	viaje	identifier	SI	INCLUDE	Included according to the investigator-provided initial classification.
key_pers_viaja	viaje	identifier	SI	INCLUDE	Included according to the investigator-provided initial classification.
key_viaje	viaje	identifier	SI	INCLUDE	Included according to the investigator-provided initial classification.
fexp_vj	viaje	expansion_weight	SI	INCLUDE	Included according to the investigator-provided initial classification.
persona__cod_per	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of cod_pers; retain the canonical selected field where applicable.
persona__cod_hg	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of cod_hg; retain the canonical selected field where applicable.
persona__nom_mun_hg	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of nom_mun_hg; retain the canonical selected field where applicable.
persona__cod_upl_hg	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of cod_upl_hg; retain the canonical selected field where applicable.
persona__cod_utam_hg	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of cod_utam_hg; retain the canonical selected field where applicable.
persona__zat_hg	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of zat_hg; retain the canonical selected field where applicable.
persona__estra_hg	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of estra_hg; retain the canonical selected field where applicable.
persona__orden	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__edad	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of edad; retain the canonical selected field where applicable.
persona__sexo	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of sexo; retain the canonical selected field where applicable.
persona__genero	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of genero; retain the canonical selected field where applicable.
persona__orien_sexual	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of orien_sexual; retain the canonical selected field where applicable.
persona__identidad_etnica	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of identidad_etnica; retain the canonical selected field where applicable.
persona__madre_cab_familia	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of madre_cab_familia; retain the canonical selected field where applicable.
persona__max_nivel_edu	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of max_nivel_edu; retain the canonical selected field where applicable.
persona__ocupacion_principal	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of ocupacion_principal; retain the canonical selected field where applicable.
persona__actividad_economica	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded by investigator decision for scope and parsimony; not documented as a duplicate of ocupacion_principal.
persona__permanencia_entre_semana	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__quien_lleva/recoge_establecimiento	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__cuidado_despues_regresar	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__condicion_discapacidad	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__RLCPD	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__cuidado_entre_semana_discap	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__dific_princ_medios_transp_discap	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__licencia_cond_vigente	persona	core_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
persona__posee_celular	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__realiza_desplazamientos	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__modo_principal_pre-pandemia	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__modo_principal_pandemia	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__razón_cambio_pandemia	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__cambio_frecuencia_post-pandemia	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__cambio_modo_pico_placa	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__cambio_modo_grandes_obra	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__cambio_modo_seguridad	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__acto_violencia_sexual	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__lugar_violencia_sexual	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__a_quien_acudio	persona	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
persona__key_hg	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of key_hg; retain the canonical selected field where applicable.
persona__key_persona	persona	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of key_pers; retain the canonical selected field where applicable.
persona__fexp_per>5años	persona	No_Repeated	Pending_duplicate_validation	PENDING	Retained in the analytical export pending resolution; no confirmed exact-copy exclusion applies.
hogar__fecha	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__cod_viv	hogar	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded by explicit investigator decision; no direct comparable counterpart was identified.
hogar__cod_hog	hogar	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded by explicit investigator decision and confirmed as an exact copy of cod_hg; key_hg remains the analytical household identifier.
hogar__cod_utam_hg	hogar	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of cod_utam_hg; retain the canonical selected field where applicable.
hogar__nom_utam_hg	hogar	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded by explicit investigator decision; no direct comparable counterpart was identified.
hogar__zat_hg	hogar	No_Repeated	Pending_duplicate_validation	EXCLUDE	Excluded as an exact value copy of zat_hg; retain the canonical selected field where applicable.
hogar__cod_upl_hg	hogar	No_Repeated	Pending_duplicate_validation	PENDING	Retained in the analytical export pending resolution; no confirmed exact-copy exclusion applies.
hogar__nom_upl_hg	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__cod_mpio_hg	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__nom_mpio_hg	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__cod_loc_hg	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__nom_loc_hg	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__estrato_hg	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__cod_dane_manzana_hg	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__tipo_enc	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__tipo_zona_hg	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__cod_barrio_vereda_hg	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__nom_barrio_vereda_hg	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__tipo_viv	hogar	extended_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
hogar__cant_hg_viv	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__perstotal_hg	hogar	core_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
hogar__pers>5años_hg	hogar	extended_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
hogar__pers>18años_hg	hogar	extended_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
hogar__ingre_mes_hg	hogar	core_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
hogar__cómo_enteró	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__key_hg	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
hogar__fexp_hg	hogar	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
stage_count	resumen de etapas	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
stage_mode_sequence	resumen de etapas	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
stage_access_minutes_sum_exploratory	resumen de etapas	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
stage_wait_minutes_sum_exploratory	resumen de etapas	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
stage_egress_minutes_sum_exploratory	resumen de etapas	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
stage_cost_sum_exploratory	resumen de etapas	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
stage_payment_sum_exploratory	resumen de etapas	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
stage_parking_cost_sum_exploratory	resumen de etapas	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
vehicle_records_in_household	resumen de vehículos	extended_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
vehicle_quantity_sum_exploratory	resumen de vehículos	No_Inicially	NO	EXCLUDE	Not selected in the investigator-provided initial classification.
vehicle_type_values	resumen de vehículos	extended_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
zat_centroid_distance_m	distancia derivada entre ZAT	core_predictor	SI	INCLUDE	Included according to the investigator-provided initial classification.
start_time_interpreted	derived: trip	derived_time	not in original classification	INCLUDE	Interpreted HH:MM value from decimal-hour source; original field preserved.
end_time_interpreted	derived: trip	derived_time	not in original classification	INCLUDE	Interpreted HH:MM value from decimal-hour source; original field preserved.
start_minutes_after_midnight	derived: trip	derived_time	not in original classification	INCLUDE	Decimal-hour value rounded after conversion to minutes.
end_minutes_after_midnight	derived: trip	derived_time	not in original classification	INCLUDE	Decimal-hour value rounded after conversion to minutes.
duration_calculated_min	derived: trip	derived_time	not in original classification	INCLUDE	End minus start modulo 24 hours; compared with reported duration.
crosses_midnight	derived: trip	quality_time	not in original classification	INCLUDE	True when interpreted end time is earlier than interpreted start time.
territory_name_ori	derived: trip	territorial_context	not in original classification	INCLUDE	Origin locality when valid; otherwise municipality; otherwise No disponible.
territory_type_ori	derived: trip	territorial_context	not in original classification	INCLUDE	Origin territory type: Localidad, Municipio, or No disponible.
territory_name_des	derived: trip	territorial_context	not in original classification	INCLUDE	Destination locality when valid; otherwise municipality; otherwise No disponible.
territory_type_des	derived: trip	territorial_context	not in original classification	INCLUDE	Destination territory type: Localidad, Municipio, or No disponible.
```
