# Research adapter contract

Source of truth: `tomato3d/light/budget.py::plant_rows`, exported by `tomato3d/cli/run_light.py`.
The adapter reads a CSV without importing or modifying research code. Exactly one row must match
plant_id + scenario_id + geometry_variant_id; ambiguous or absent selections are rejected.

| CSV column | Product metric | Unit |
|---|---|---|
| leaf_area_mm2 | leaf_area | mm2 |
| intercepted_full_output_umol_s | intercepted_full_output | umol/s |
| absorbed_full_output_umol_s | absorbed_full_output | umol/s |
| intercepted_mol_day | intercepted_daily | mol/day |
| absorbed_mol_day | absorbed_daily | mol/day |
| leaf_ppfd_cv | leaf_ppfd_cv | dimensionless |
| Not exported | plant_height | mm, unavailable |
| Not exported | canopy_area | mm2, unavailable |

All numeric light output is `model_estimated`, never promoted to measured. `unavailable` becomes
SQL NULL plus status `unavailable`. NaN, infinity, negatives and wrong units fail validation.
Leaf area is a sum of modelled leaf surfaces, NOT projected canopy footprint. No PPFD/lux conversion,
height inference, organ-area aggregation or coordinate conversion is performed.

The caller declares observation time and evidence (`research_model` or `synthetic_fixture`), since
the plant CSV has neither. File checksum, file name, scenario and variant are kept with each import.
This is caller-declared provenance, not cryptographic certification of physical measurements.
Import IDs are replay-safe; changing a file or metadata under the same ID fails with 409.

P1 `areas.csv` integration is deferred: visible projected area, completed projected area and
one-sided lamina area are distinct and may overlap across organs/views. Summing them into a
whole-plant leaf area would invent unsupported semantics. `plant_height` and `canopy_area` are
reserved explicit missing metrics until a validated producer/aggregation contract is agreed.
Full run_summary/model-limit ingestion and P1 manifest validation are subsequent work.
