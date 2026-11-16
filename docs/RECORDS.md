# Record contract — version 1

The Python validator in `researchos_hi/core.py` is the executable contract. Unknown metadata fields are retained. JSON must not contain duplicate keys, NaN or Infinity.

| Field | Required content |
| --- | --- |
| `schema_version` | Integer `1` |
| `id` | 1–80 lowercase letters, digits, underscores or hyphens; starts with a letter or digit |
| `title`, `owner`, `hypothesis` | Nonempty strings |
| `data_kind` | `synthetic`, `simulation`, or `experimental`; applies to all declared input measurements |
| `protocol` | Object with nonempty `method` and `reference`; extend with equipment, parameters, orientation and calibration references |
| `substrate` | Object with `material` and positive finite `lattice_constant_A` |
| `layers` | 1–1000 objects in deposition order, each with unique `id`, `material`, positive `thickness_nm` and `lattice_constant_A` |
| `measurements` | Array of layer-specific characterization values, possibly empty |
| `targets` | Array of owner-defined layer/metric comparisons, possibly empty |
| `evidence` | Array of evidence declarations; experimental records require at least one |

## Measurements and targets

Each measurement contains `layer_id`, `metric`, nonnegative finite `value` and `uncertainty`, nonempty `method`, and an `evidence_ids` array referring to declared evidence. Experimental measurements require at least one reference. There can be only one measurement per layer/metric; aggregate repeated measurements separately and retain raw observations as evidence. Do not mix synthetic and real values in one experimental record.

| Metric | Unit | Measurement considerations |
| --- | --- | --- |
| `roughness_rms_nm` | nm RMS | Specify scan area, filtering, preparation and instrument |
| `interface_width_nm` | nm | Define the composition transition or other width convention and spatial resolution |
| `defect_density_cm2` | cm⁻² | Define defect type, counting area, detection limit and sampling |
| `mobility_cm2_Vs` | cm²/(V·s) | State device geometry, extraction method and measurement conditions |

Uncertainty is a declared nonnegative value in the same unit as its measurement. Its coverage factor, confidence interval or standard uncertainty interpretation must be described in the method/metadata. This runner stores uncertainty but does not propagate it or use it for target decisions.

Each target contains `layer_id`, `metric`, `operator` (`<=` or `>=`), nonnegative finite `value`, and `rationale`. Targets are user criteria, not preloaded program requirements. One target per layer/metric is supported. Output status is `met`, `unmet`, or `no-data`, alongside its input data kind. A met synthetic target is not an experimental achievement.

## Evidence

Each declaration contains unique `id`, unique relative `path`, lowercase 64-character `sha256`, and nonempty `description`. Put protocol/calibration records in this list too when applicable. Paths must stay inside the record directory after resolving symlinks. Absolute paths, drive paths and directory traversal are rejected.

Run `researchos-hi hash <file>` to obtain a digest. The runner verifies and captures each file into the bundle under a generated name; `manifest.json` maps evidence IDs to those names. Verification works even if the original file location is no longer available.

Evidence checks verify declared bytes and links, not whether a characterization method is appropriate or measurements are genuine. Check sample identity, calibration, chain of custody and uncertainty independently.
