# Stack geometry screening v1

The built-in analysis performs arithmetic on declared inputs. It is intentionally not a synthesis, epitaxy or process simulation.

## Geometry

Layers are ordered from the substrate upward. Total deposited thickness is the sum of layer thicknesses, excluding substrate thickness. Interface depth for a layer is the sum of preceding deposited layer thicknesses; the substrate/first-layer interface is depth zero.

For each interface, nominal scalar lattice mismatch is:

`mismatch_percent = 100 × (a_above / a_below − 1)`

Both lattice constants use ångströms. Positive mismatch means the declared upper scalar constant is larger. This nominal ratio ignores crystallographic orientation, surface mesh matching, anisotropy, thermal expansion, interlayers, relaxation and strain. It must not be interpreted as a predicted defect density or feasible epitaxial pairing. Values in the example are fictional.

## Target comparisons

A declared measurement is compared directly with its owner-defined threshold. Values exactly on a threshold meet it. Uncertainty is recorded but not evaluated; detection limits and zero observed defects need separate scientific interpretation. Missing measurements yield `no-data`. Output always retains the input data kind. None of these checks establishes program compliance or material quality.

## Reproducibility and integrity

The runner captures the exact input bytes and verified evidence, generates JSON/CSV/Markdown, and hashes every artifact except the manifest itself. Output contains no clock or random state. Repeated runs with identical bytes yield identical artifacts under the same runner behavior. Re-verification checks file hashes, evidence-to-record hashes and recomputes `results.json`.

This is not a signed, append-only or tamper-proof audit service. Bundles are writable files; the CLI refuses to overwrite existing directories but does not prevent external edits. Use versioned external storage and independent review when provenance assurance is needed. Scientific models added later need explicit derivation, supported parameter domains, reference benchmarks and validation evidence.
