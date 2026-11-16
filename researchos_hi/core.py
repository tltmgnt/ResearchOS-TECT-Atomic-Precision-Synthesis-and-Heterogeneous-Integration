"""Validated records, immutable output directories and evidence integrity checks."""
import csv
import hashlib
import io
import json
import math
import re
import shutil
import tempfile
from pathlib import Path

VERSION = "0.1.0"
LIMITATIONS = (
    "Geometric screening only. Nominal scalar lattice mismatch is not an epitaxy, "
    "strain, defect, growth-kinetics or device-performance prediction. Target checks "
    "compare declared values, without uncertainty propagation or independent review. "
    "Neither a passing target check nor a matching checksum proves defect-free "
    "synthesis, an atomically sharp interface, authenticity, or DARPA compliance."
)
METRICS = {"roughness_rms_nm", "interface_width_nm", "defect_density_cm2", "mobility_cm2_Vs"}


class ValidationError(ValueError):
    pass


def dumps(obj):
    return json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_json(data):
    def reject_constant(value):
        raise ValidationError(f"non-finite JSON constant: {value}")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValidationError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(data,
                      parse_constant=reject_constant, object_pairs_hook=unique)


def read_json(path):
    return parse_json(Path(path).read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def text(value, name):
    require(isinstance(value, str) and bool(value.strip()), f"{name} must be a nonempty string")


def numeric(value, name, positive=False):
    require(type(value) in (float, int), f"{name} must be numeric")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    require(finite and (value > 0 if positive else value >= 0),
            f"{name} must be finite and {'positive' if positive else 'nonnegative'}")


def safe_path(value):
    text(value, "evidence path")
    p = Path(value)
    require(not p.is_absolute() and not any(x in ("..", ".") for x in value.split("/"))
            and "\\" not in value and not re.match(r"^[A-Za-z]:", value),
            "evidence path must be relative and cannot traverse directories")
    return p


def validate(record):
    require(isinstance(record, dict), "record must be an object")
    require(type(record.get("schema_version")) is int and record["schema_version"] == 1,
            "schema_version must be integer 1")
    require(isinstance(record.get("id"), str) and bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", record["id"])), "invalid record id")
    for key in ("title", "owner", "hypothesis"):
        text(record.get(key), key)
    require(record.get("data_kind") in ("synthetic", "simulation", "experimental"), "invalid data_kind")
    protocol = record.get("protocol")
    require(isinstance(protocol, dict), "protocol must be an object")
    for key in ("method", "reference"):
        text(protocol.get(key), f"protocol.{key}")
    substrate = record.get("substrate")
    require(isinstance(substrate, dict), "substrate must be an object")
    text(substrate.get("material"), "substrate.material")
    numeric(substrate.get("lattice_constant_A"), "substrate.lattice_constant_A", True)
    layers = record.get("layers")
    require(isinstance(layers, list) and 1 <= len(layers) <= 1000, "layers must contain 1–1000 objects")
    ids = set()
    for layer in layers:
        require(isinstance(layer, dict), "layer must be an object")
        text(layer.get("id"), "layer.id")
        require(layer["id"] not in ids, "duplicate layer id")
        ids.add(layer["id"])
        text(layer.get("material"), "layer.material")
        numeric(layer.get("thickness_nm"), "layer.thickness_nm", True)
        numeric(layer.get("lattice_constant_A"), "layer.lattice_constant_A", True)
    evidence = record.get("evidence")
    require(isinstance(evidence, list), "evidence must be an array")
    evidence_ids, paths = set(), set()
    for item in evidence:
        require(isinstance(item, dict), "evidence entry must be an object")
        text(item.get("id"), "evidence.id")
        safe_path(item.get("path"))
        require(item["id"] not in evidence_ids and item["path"] not in paths, "duplicate evidence id or path")
        evidence_ids.add(item["id"])
        paths.add(item["path"])
        require(isinstance(item.get("sha256"), str) and bool(re.fullmatch(r"[a-f0-9]{64}", item["sha256"])), "invalid evidence sha256")
        text(item.get("description"), "evidence.description")
    require(record["data_kind"] != "experimental" or bool(evidence), "experimental records require evidence")
    measurements = record.get("measurements")
    require(isinstance(measurements, list), "measurements must be an array")
    seen = set()
    for item in measurements:
        require(isinstance(item, dict), "measurement must be an object")
        key = (item.get("layer_id"), item.get("metric"))
        require(isinstance(key[0], str) and key[0] in ids and isinstance(key[1], str) and key[1] in METRICS,
                "measurement needs a valid layer_id and supported metric")
        require(key not in seen, "duplicate layer/metric measurement")
        seen.add(key)
        numeric(item.get("value"), "measurement.value")
        numeric(item.get("uncertainty"), "measurement.uncertainty")
        text(item.get("method"), "measurement.method")
        refs = item.get("evidence_ids")
        require(isinstance(refs, list) and all(isinstance(ref, str) and ref in evidence_ids for ref in refs), "unknown evidence reference")
        require(record["data_kind"] != "experimental" or bool(refs), "experimental measurements require evidence references")
    targets = record.get("targets")
    require(isinstance(targets, list), "targets must be an array")
    target_keys = set()
    for target in targets:
        require(isinstance(target, dict), "target must be an object")
        key = (target.get("layer_id"), target.get("metric"))
        require(isinstance(key[0], str) and key[0] in ids and isinstance(key[1], str) and key[1] in METRICS, "invalid target layer/metric")
        require(key not in target_keys, "duplicate target layer/metric")
        target_keys.add(key)
        require(target.get("operator") in ("<=", ">="), "target operator must be <= or >=")
        numeric(target.get("value"), "target.value")
        text(target.get("rationale"), "target.rationale")
    return record


def evidence_content(root, relative):
    root = Path(root).resolve()
    path = (root / safe_path(relative)).resolve()
    require(path.is_relative_to(root), "evidence resolves outside record directory")
    return path.read_bytes()


def verify_evidence(record, root):
    verified = []
    for item in record["evidence"]:
        data = evidence_content(root, item["path"])
        require(sha(data) == item["sha256"], f"checksum mismatch: {item['path']}")
        verified.append((item, data))
    return verified


def analyze(record):
    validate(record)
    below = record["substrate"]
    depth = 0.0
    interfaces = []
    for layer in record["layers"]:
        mismatch = 100 * (layer["lattice_constant_A"] / below["lattice_constant_A"] - 1)
        interfaces.append({"below_material": below["material"], "above_layer_id": layer["id"],
                           "above_material": layer["material"], "depth_nm": depth,
                           "nominal_mismatch_percent": mismatch})
        depth += layer["thickness_nm"]
        below = layer
    values = {(m["layer_id"], m["metric"]): m for m in record["measurements"]}
    checks = []
    for target in record["targets"]:
        measurement = values.get((target["layer_id"], target["metric"]))
        status = "no-data"
        if measurement:
            value = measurement["value"]
            met = value <= target["value"] if target["operator"] == "<=" else value >= target["value"]
            status = "met" if met else "unmet"
        checks.append({"target": target, "measurement": measurement, "status": status,
                       "basis": record["data_kind"]})
    result = {"analysis": "stack-geometry-v1", "runner_version": VERSION,
              "data_kind": record["data_kind"], "total_thickness_nm": depth,
              "interfaces": interfaces, "target_checks": checks, "limitations": LIMITATIONS}
    dumps(result)  # Reject non-finite derived results before producing artifacts.
    return result


def report(record, result):
    lines = [f"# {record['id']}", "", record["title"], "", f"Input basis: **{record['data_kind']}**.",
             "", result["limitations"], "", f"Total deposited thickness: {result['total_thickness_nm']:g} nm.",
             "", "| Layer | Nominal mismatch (%) | Interface depth (nm) |", "| --- | ---: | ---: |"]
    for item in result["interfaces"]:
        label = item['above_layer_id'].replace('|', '\\|').replace('\n', ' ')
        lines.append(f"| {label} | {item['nominal_mismatch_percent']:.6g} | {item['depth_nm']:g} |")
    lines += ["", "## User-defined targets", "", "These are record-owner criteria, not verified DARPA requirements. Missing values stay no-data.", ""]
    for item in result["target_checks"]:
        t = item["target"]
        lines.append(f"- {t['layer_id']} / {t['metric']}: **{item['status']}** ({item['basis']} inputs).")
    if not result["target_checks"]:
        lines.append("No targets declared.")
    return "\n".join(lines) + "\n"


def run(record_path, output):
    record_path, output = Path(record_path), Path(output)
    require(not output.exists(), "output already exists; choose a new run directory")
    raw = record_path.read_bytes()
    record = validate(parse_json(raw.decode("utf-8")))
    evidence = verify_evidence(record, record_path.parent)
    result = analyze(record)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".researchos-", dir=output.parent))
    try:
        (staging / "record.json").write_bytes(raw)
        (staging / "results.json").write_text(dumps(result), encoding="utf-8")
        (staging / "report.md").write_text(report(record, result), encoding="utf-8")
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=list(result["interfaces"][0]))
        writer.writeheader()
        writer.writerows(result["interfaces"])
        (staging / "interfaces.csv").write_text(buf.getvalue(), encoding="utf-8")
        for i, (_, data) in enumerate(evidence):
            dest = staging / "evidence" / f"{i:04d}.bin"
            dest.parent.mkdir(exist_ok=True)
            dest.write_bytes(data)
        files = {p.relative_to(staging).as_posix(): sha(p.read_bytes())
                 for p in sorted(staging.rglob("*")) if p.is_file()}
        manifest = {"schema_version": 1, "files": files,
                    "evidence_map": [{"id": item["id"], "bundle_path": f"evidence/{i:04d}.bin"}
                                     for i, (item, _) in enumerate(evidence)]}
        (staging / "manifest.json").write_text(dumps(manifest), encoding="utf-8")
        # mkdir exclusively reserves the output without replacing earlier runs.
        output.mkdir()
        for p in staging.iterdir():
            shutil.move(str(p), output / p.name)
    finally:
        shutil.rmtree(staging)
    return result


def verify_bundle(root):
    root = Path(root)
    manifest = read_json(root / "manifest.json")
    require(isinstance(manifest, dict) and manifest.get("schema_version") == 1, "invalid manifest")
    files = manifest.get("files")
    require(isinstance(files, dict) and {"record.json", "results.json", "report.md", "interfaces.csv"} <= files.keys(), "incomplete manifest")
    for name, expected in files.items():
        require(isinstance(expected, str) and bool(re.fullmatch(r"[a-f0-9]{64}", expected)), "invalid manifest digest")
        require(sha(evidence_content(root, name)) == expected, f"bundle checksum mismatch: {name}")
    record = validate(read_json(root / "record.json"))
    require(read_json(root / "results.json") == analyze(record), "results do not reproduce from record")
    expected_map = [{"id": item["id"], "bundle_path": f"evidence/{i:04d}.bin"} for i, item in enumerate(record["evidence"])]
    require(manifest.get("evidence_map") == expected_map, "invalid evidence map")
    for mapping, item in zip(expected_map, record["evidence"]):
        require(mapping["bundle_path"] in files, "evidence absent from manifest")
        require(sha(evidence_content(root, mapping["bundle_path"])) == item["sha256"], "evidence no longer matches record")
    return manifest
