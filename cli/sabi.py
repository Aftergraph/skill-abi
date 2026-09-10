#!/usr/bin/env python3
"""sabi reference CLI: validate, inspect, resolve, diff, test, certify,
verify-certificate, lock. Exit codes: 0 ok, 1 conformance failure,
2 usage error. --json emits machine-readable output where supported.
"""
import argparse
import hashlib
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


def cmd_validate(args):
    from sabi.certify import evaluate_invariants  # noqa: F401  (contract presence)
    skill = Path(args.skill)
    errors = []
    sm = skill / "SKILL.md"
    if not sm.is_file():
        errors.append("SKILL.md missing")
    else:
        text = sm.read_bytes().decode("utf-8")
        if not text.startswith("---"):
            errors.append("SKILL.md must start with ---")
    abi_p = skill / "skill.abi.yaml"
    if abi_p.is_file():
        try:
            abi = _load_yaml(abi_p)
            for k in ("spec", "skill", "inputs", "outputs", "capabilities"):
                if k not in (abi or {}):
                    errors.append(f"abi missing key: {k}")
        except Exception as exc:
            errors.append(f"abi YAML error: {exc}")
    else:
        errors.append("skill.abi.yaml missing")
    ok = not errors
    if args.json:
        print(json.dumps({"skill": skill.name, "valid": ok, "errors": errors}))
    else:
        print(f"{skill.name}: {'VALID' if ok else 'INVALID'}")
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
    from sabi.resolver import resolve_tier
    skill = Path(args.skill)
    prof = _load_yaml(args.runtime)
    deg = (_load_yaml(skill / "degradation.yaml") or {}).get("degradation", {})
    tier = resolve_tier(deg, prof.get("capabilities", []) or [])
    if args.json:
        print(json.dumps({"runtime": prof.get("runtime"), "tier": tier}))
    else:
        print(f"Resolved tier: {(tier or 'NONE').upper()}")
    return 0


def cmd_diff(args):
    from sabi.diff import semantic_diff
    bump, breaking, minor, notes = semantic_diff(args.old, args.new)
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
    print(f"certificate: {cert['certificate']} ({cert['passed']}/{cert['cases']}), unsigned")
    return 0 if cert["failed"] == 0 else 1


def cmd_verify_certificate(args):
    cert = json.loads(Path(args.certificate).read_text(encoding="utf-8"))
    problems = []
    for k in ("skill", "skill_digest", "abi_digest", "cases", "passed", "failed"):
        if k not in cert:
            problems.append(f"missing field: {k}")
    if cert.get("passed", 0) + cert.get("failed", 0) != cert.get("cases", -1):
        problems.append("passed+failed != cases")
    if cert.get("signed"):
        problems.append("signed=true requires detached signature check (see sabi-sign)")
    if problems:
        print("INVALID")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"certificate structural OK: {cert.get('certificate')} ({cert.get('passed')}/{cert.get('cases')})")
    return 0


def cmd_lock(args):
    skill = Path(args.skill)
    pats = ["SKILL.md", "skill.abi.yaml", "effects.yaml", "degradation.yaml",
            "schemas/*.json", "scripts/*.py", "references/*", "bindings/*.yaml",
            "conformance/*.yaml"]
    files = {}
    for pat in pats:
        for p in sorted(skill.glob(pat)):
            if p.is_file() and p.name != "skill.lock":
                files[p.relative_to(skill).as_posix()] = "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()
    doc = {"lock_version": 1, "skill": skill.name, "files": files}
    (skill / "skill.lock").write_bytes((json.dumps(doc, indent=2) + "\n").encode("utf-8"))
    print(f"lock written: {len(files)} files")
    return 0


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
    p = sub.add_parser("verify-certificate"); p.add_argument("certificate"); p.set_defaults(fn=cmd_verify_certificate)
    p = sub.add_parser("lock"); p.add_argument("skill"); p.set_defaults(fn=cmd_lock)
    p = sub.add_parser("export"); p.add_argument("skill"); p.set_defaults(fn=cmd_export)
    args = ap.parse_args(raw)
    args.json = args.json or json_flag
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
