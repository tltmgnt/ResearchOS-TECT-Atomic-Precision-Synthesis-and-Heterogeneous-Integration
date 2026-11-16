# ResearchOS TECT — Atomic-Precision Synthesis and Heterogeneous Integration

Independent research workspace aligned with DARPA M-STUDIO goals, supporting reproducible modeling, synthesis experiment tracking, and evidence-linked validation of nanoscale multilayer semiconductor structures and heterogeneous material interfaces.

This repository is standalone. It does not depend on the SynQuaNon repository, superconducting models, or its app. TECT is retained as the project identifier without an assumed expansion.

## What works now

- Validate substrate, ordered layer stacks, synthesis protocol references, measurements with uncertainty, evidence references, and user-defined targets.
- Screen total deposited thickness and nominal scalar lattice mismatch at each adjacent interface.
- Compare declared characterization measurements with owner-defined targets. Missing measurements remain `no-data`; every comparison preserves its synthetic/simulation/experimental basis.
- Verify SHA-256 evidence checksums and capture original record/evidence bytes in a portable run bundle.
- Export interface CSV, JSON results, and a Markdown report. Re-verify bundle integrity and independently reproduce numerical results from the included record.

The example uses fictional materials and synthetic values. This software does not synthesize materials, control equipment, predict defect density, establish atomic precision, or validate device performance. It claims no DARPA affiliation, award, endorsement, or open solicitation.

## Quick start

Python 3.10 or newer; no third-party runtime dependencies. From the repository root:

```bash
python -m researchos_hi validate examples/synthetic-stack.json
python -m researchos_hi run examples/synthetic-stack.json --output runs/demo
python -m researchos_hi verify runs/demo
python -m researchos_hi report runs/demo
python -m unittest discover -s tests -v
```

Optional installation enables `researchos-hi`:

```bash
python -m pip install .
researchos-hi --help
```

The demo contains 4 nm and 6 nm fictional layers. It yields 10 nm total deposited thickness, approximately 2% and 1.96078% nominal adjacent lattice mismatch, one synthetic target marked `met`, and one target marked `no-data`. These are bookkeeping checks, not scientific achievements.

## Bring your own experiment

1. Copy `examples/synthetic-stack.json` to a new experiment directory and assign an ID, owner, hypothesis and honest `data_kind`.
2. Define the substrate and layers in deposition order. Use nanometers for thickness and ångströms for nominal scalar lattice constants.
3. Replace the placeholder protocol with an actual versioned protocol reference. Additional protocol metadata can capture equipment, process parameters, calibration, orientation, and sample preparation.
4. Put authorized evidence files under the record directory. Run `researchos-hi hash path/to/file`, then declare each file's relative path, digest, description and unique evidence ID.
5. Enter measurements with a method, uncertainty and evidence references. Experimental records require evidence, and their measurements require references. Define your own targets with a rationale.
6. Validate, run into a **new** output directory, verify, and review. Existing output directories are rejected to preserve earlier runs.

Source paths are resolved under the record directory; traversal and symlinks outside it are rejected. The runner captures verified evidence bytes. Keep private, unpublished, or restricted data out of this public repository. Local bundles are ignored by Git.

## Bundle contents

| File | Purpose |
| --- | --- |
| `record.json` | Exact original input bytes |
| `results.json` | Geometry, target comparisons, input basis and limitations |
| `interfaces.csv` | Adjacent interface geometry and nominal mismatch |
| `report.md` | Human-readable result and missing-data summary |
| `evidence/0000.bin`, … | Captured original evidence bytes; mappings in manifest |
| `manifest.json` | File digests and evidence ID-to-bundle path mapping |

Bundles are deterministic for identical input bytes, evidence and runner behavior. Checksums are not signatures: someone who can replace all records and hashes can forge a bundle. Independent provenance review remains necessary.

## Documentation

- [Record contract](docs/RECORDS.md)
- [Screening model and limitations](docs/MODEL.md)
- [Research plan and acceptance evidence](docs/RESEARCH_PLAN.md)
- [Primary sources and opportunity context](docs/SOURCES.md)
- [Contributing](CONTRIBUTING.md)

CI installs the package and runs tests plus the full example workflow across Python 3.10–3.13. Generated synthetic bundles are uploaded as workflow artifacts. The existing [license](LICENSE) is preserved.
