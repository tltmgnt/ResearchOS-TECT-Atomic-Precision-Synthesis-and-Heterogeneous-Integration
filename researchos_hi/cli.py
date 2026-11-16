"""Command-line interface for standalone ResearchOS TECT HI workflows."""
import argparse
import sys
from pathlib import Path
from .core import ValidationError, analyze, read_json, report, run, sha, validate, verify_bundle, verify_evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "run", "report", "hash", "verify"):
        p = sub.add_parser(command)
        p.add_argument("path", type=Path)
        if command == "run":
            p.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "hash":
            print(sha(args.path.read_bytes()))
        elif args.command == "validate":
            record = validate(read_json(args.path))
            verify_evidence(record, args.path.parent)
            analyze(record)
            print("Record valid; declared evidence checksums verified. Scientific validity not assessed.")
        elif args.command == "run":
            run(args.path, args.output)
            print(f"Created run bundle: {args.output}")
        elif args.command == "verify":
            verify_bundle(args.path)
            print("Bundle checksums and numerical reproduction verified. Not an authenticity attestation.")
        else:
            verify_bundle(args.path)
            print(report(read_json(args.path / "record.json"), read_json(args.path / "results.json")), end="")
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
