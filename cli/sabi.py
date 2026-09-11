#!/usr/bin/env python3
"""sabi reference CLI: validate, inspect, resolve, diff, test, certify,
verify-certificate, lock, bind, verify-lock.

Exit codes:
  0  OK
  1  validation / binding failure
  2  usage error
  3  integrity / lock / tamper
  4  signature / certificate

All commands support --json for machine-readable output where applicable.
The CLI is a thin entry point: every command delegates to the sabi library.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    import yaml
except ImportError:
    sys.exit("sabi: pyyaml is required")


def _load_yaml(p):
    return yaml.safe_load(Path(p).read_text(encoding="utf-8"))


def _repo_root():
    return Path(__file__).resolve().parents[1]


def cmd_validate(args):
    """Validate a skill directory (one canonical path: api.validate_canonical)."""
    from sabi.api import validate_canonical
    from sabi.errors import SabiError
    skill = Path(args.skill)
    schemas_dir = Path(__file__).resolve().parents[1] / "schemas"
    try:
        result = validate_canonical(skill, schemas_dir=schemas_dir)
    except SabiError as exc:
        print(f"{skill.name}: ERROR ({exc})")
        return exc.exit_code
    level = result["level"]
    errors = result["errors"]
    ok = len(errors) == 0
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{skill.name}: {'VALID' if ok else 'INVALID'} ({level})")
        for e in errors:
            print(f"  - {e}")
    return 0 if ok else 1


def cmd_inspect(args):
    abi = _load_yaml(Path(args.skill) / "skill.abi.yaml")
    eff = _load_yaml(Path(args.skill) / "effects.yaml").get("effects", {})
    caps = (abi.get("capabilities", {}) or {})
    out = {
        "skill": f"{abi.get('skill')}@{abi.get('version')}",
        "required": caps.get("required", []) or [],
        "optional": caps.get("optional", []) or [],
        "effects": {k: v for k, v in eff.items()},
    }
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Skill: {out['skill']}")
        print(f"Required: {', '.join(out['required']) or '(none)'}")
        print(f"Optional: {', '.join(out['optional']) or '(none)'}")
        print(f"Effects: {json.dumps(out['effects'])}")
    return 0


def cmd_resolve(args):
    from sabi.api import resolve
    skill = Path(args.skill)
    prof = _load_yaml(args.runtime)
    deg = (_load_yaml(skill / "degradation.yaml") or {}).get("degradation", {})
    tier = resolve(deg, prof.get("capabilities", []) or [])
    if args.json:
        print(json.dumps({"runtime": prof.get("runtime"), "tier": tier}))
    else:
        print(f"Resolved tier: {(tier or 'NONE').upper()}")
    return 0


def cmd_diff(args):
    from sabi.api import diff
    bump, breaking, minor, notes = diff(args.old, args.new)
    if args.json:
        print(json.dumps({"bump": bump, "breaking": breaking, "minor": minor, "notes": notes}, indent=2))
    else:
        for b in breaking:
            print(f"  BREAKING: {b}")
        for m in minor:
            print(f"  minor: {m}")
        print(f"Recommended version bump: {bump}")
    return 0


def cmd_test(args):
    from sabi.certify import evaluate_invariants
    from sabi.resolver import resolve_tier
    skill = Path(args.skill)
    profiles = sorted((skill / "bindings").glob("*.yaml")) if args.matrix else [None]
    total_fail = 0
    results = []
    for prof_p in profiles:
        caps = _load_yaml(prof_p).get("capabilities", []) if prof_p else []
        deg = (_load_yaml(skill / "degradation.yaml") or {}).get("degradation", {})
        tier = resolve_tier(deg, caps)
        res = evaluate_invariants(skill, caps)
        fails = sum(1 for _, ok in res if not ok)
        total_fail += fails
        results.append({"runtime": prof_p.stem if prof_p else "default",
                        "tier": tier, "passed": len(res) - fails, "failed": fails})
    if args.json:
        print(json.dumps({"skill": skill.name, "results": results}, indent=2))
    else:
        for r in results:
            print(f"{r['runtime']}: tier {str(r['tier']).upper()} {r['passed']}/{r['passed'] + r['failed']}")
    return 1 if total_fail else 0


def cmd_certify(args):
    from sabi.certify import evaluate_invariants, build_certificate
    from sabi.resolver import resolve_tier
    skill = Path(args.skill)
    if not (skill / "skill.lock").is_file():
        print("certify: skill.lock missing (run `sabi lock` first)")
        return 1
    deg = (_load_yaml(skill / "degradation.yaml") or {}).get("degradation", {})
    records = []
    for prof_p in sorted((skill / "bindings").glob("*.yaml")):
        prof = _load_yaml(prof_p)
        caps = prof.get("capabilities", []) or []
        records.append((prof.get("runtime", prof_p.stem),
                        resolve_tier(deg, caps),
                        evaluate_invariants(skill, caps)))
    cert = build_certificate(skill, records)
    out = skill / "attestations" / "portability.json"
    out.parent.mkdir(exist_ok=True)
    out.write_bytes((json.dumps(cert, indent=2) + "\n").encode("utf-8"))
    print(f"certificate: {cert['evidence_class']} "
          f"({cert['passed']}/{cert['cases']}), unsigned")
    return 0 if cert["failed"] == 0 else 1


def cmd_verify_certificate(args):
    from sabi.api import verify_certificate
    from sabi.errors import SabiError
    cert_path = Path(args.certificate)
    skill_path = Path(args.skill) if args.skill else None
    try:
        result = verify_certificate(cert_path, skill_dir=skill_path)
    except SabiError as exc:
        print(f"CERTIFICATE ERROR ({exc})")
        return exc.exit_code
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        ok = result.get("valid", False)
        print(f"{'VALID' if ok else 'INVALID'}: {result.get('certificate', '?')} "
              f"({result.get('passed')}/{result.get('cases')})")
        for p in result.get("problems", []):
            print(f"  - {p}")
    return 0 if result.get("valid", False) else 1


def cmd_lock(args):
    from sabi.api import lock
    skill = Path(args.skill)
    n = lock(skill)
    print(f"lock written: {n} files")
    return 0


def cmd_verify_lock(args):
    from sabi.api import verify_lock
    from sabi.errors import SabiError
    skill = Path(args.skill)
    try:
        result = verify_lock(skill)
    except SabiError as exc:
        print(f"LOCK ERROR ({exc})")
        return exc.exit_code
    ok = result.get("ok", False)
    errors = result.get("errors", [])
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if ok:
            print(f"{skill.name}: lock OK ({result.get('files', 0)} files)")
        else:
            print(f"{skill.name}: LOCK INVALID")
            for e in errors:
                print(f"  - {e}")
    return 0 if ok else (3 if errors else 1)


def cmd_bind(args):
    from sabi.api import bind
    from sabi.errors import SabiError
    skill = Path(args.skill)
    prof = _load_yaml(args.runtime)
    try:
        result = bind(skill, prof)
    except SabiError as exc:
        print(f"BIND ERROR ({exc})")
        return exc.exit_code
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Binding: {result.get('skill')} -> {result.get('runtime_profile', {}).get('runtime', '?')}")
        print(f"  Tier: {result.get('selected_degradation_tier', 'NONE').upper()}")
        unresolved = result.get("unresolved_required_caps", [])
        if unresolved:
            print(f"  Unresolved required caps: {unresolved}")
        else:
            print("  All required caps resolved")
        print(f"  Effect envelope: {result.get('effect_envelope_ref', '?')}")
    return 0 if not unresolved else 1


def cmd_export(args):
    """Export requirement-object JSON for a skill directory."""
    from sabi.api import export_requirement_object
    obj = export_requirement_object(Path(args.skill))
    if args.json:
        print(json.dumps(obj, indent=2))
    else:
        out = Path(args.skill) / "requirement-object.json"
        out.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"requirement object written: {out}")
    return 0


def main(argv=None):
    raw = list(argv if argv is not None else sys.argv[1:])
    json_flag = False
    if "--json" in raw:
        json_flag = True
        raw = [a for a in raw if a != "--json"]
    ap = argparse.ArgumentParser(prog="sabi")
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate"); p.add_argument("skill"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("inspect"); p.add_argument("skill"); p.set_defaults(fn=cmd_inspect)
    p = sub.add_parser("resolve"); p.add_argument("skill"); p.add_argument("--runtime", required=True); p.set_defaults(fn=cmd_resolve)
    p = sub.add_parser("diff"); p.add_argument("old"); p.add_argument("new"); p.set_defaults(fn=cmd_diff)
    p = sub.add_parser("test"); p.add_argument("skill"); p.add_argument("--matrix", action="store_true"); p.set_defaults(fn=cmd_test)
    p = sub.add_parser("certify"); p.add_argument("skill"); p.set_defaults(fn=cmd_certify)
<<<<<<< HEAD
    p = sub.add_parser("verify-certificate"); p.add_argument("certificate"); p.add_argument("--skill"); p.set_defaults(fn=cmd_verify_certificate)
=======
    p = sub.add_parser("verify-certificate"); p.add_argument("certificate"); p.add_argument("--skill", default=None); p.set_defaults(fn=cmd_verify_certificate)
>>>>>>> wt-abc
    p = sub.add_parser("lock"); p.add_argument("skill"); p.set_defaults(fn=cmd_lock)
    p = sub.add_parser("verify-lock"); p.add_argument("skill"); p.set_defaults(fn=cmd_verify_lock)
    p = sub.add_parser("bind"); p.add_argument("skill"); p.add_argument("--runtime", required=True); p.set_defaults(fn=cmd_bind)
    p = sub.add_parser("export"); p.add_argument("skill"); p.set_defaults(fn=cmd_export)

    args = ap.parse_args(raw)
    args.json = args.json or json_flag
    try:
        return args.fn(args)
    except Exception as exc:
        print(f"sabi: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
