# Analytical Dataset Design

This notebook builds the first local, source-preserving trip-level dataset from the validated SQLite layer. The data product is excluded from Git.

- `em2023_trip_dataset.csv`: one row per `viajes` record, retaining all source fields and values as text.
- `docs/data_dictionary/analytical_trip_dataset_fields.csv`: field lineage and provisional analytical role labels.

The expansion field is retained but is not applied. The OD matrix is a later product and requires separately validated survey-weight and ZAT rules.
