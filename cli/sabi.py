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


def _repo_root():
    return Path(__file__).resolve().parents[1]


def cmd_validate(args):
    from sabi.validator import validate_skill
    skill = Path(args.skill)
    level, errors = validate_skill(skill)
    ok = not errors and level != "INVALID"
    if args.json:
        print(json.dumps({"skill": skill.name, "valid": ok, "level": level,
                          "errors": errors}))
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
    """Verify a certificate against the skill it claims to describe.

    Structural JSON validity alone is not sufficient: the certificate
    schema, digests vs actual bytes, lock digest, run-receipt references,
    runtime/test-suite identifiers, evidence existence, and signature
    bundle are all checked.
    """
    from sabi import schema as json_schema
    from sabi.certify import EVIDENCE_CLASSES, file_digest

    cert_path = Path(args.certificate)
    if not cert_path.is_file():
        print("INVALID")
        print(f"  - certificate not found: {cert_path}")
        return 1
    try:
        cert = json.loads(cert_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print("INVALID")
        print(f"  - certificate is not valid JSON: {exc}")
        return 1
    if not isinstance(cert, dict):
        print("INVALID")
        print("  - certificate must be a JSON object")
        return 1

    problems = []

    # 1. certificate schema (not just structural JSON validity)
    schema_path = _repo_root() / "schemas" / "certificate.schema.json"
    if schema_path.is_file():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        for msg in json_schema.validate(cert, schema):
            problems.append(f"schema: {msg}")
    else:
        problems.append("certificate schema not found")

    # 2. required fields
    for k in ("skill", "skill_digest", "abi_digest", "sabi", "cases",
              "passed", "failed", "evidence_class", "signed"):
        if k not in cert:
            problems.append(f"missing field: {k}")

    # 3. counts
    if all(isinstance(cert.get(k), int) for k in ("cases", "passed", "failed")):
        if cert["passed"] + cert["failed"] != cert["cases"]:
            problems.append("passed+failed != cases")
        if min(cert["cases"], cert["passed"], cert["failed"]) < 0:
            problems.append("counts must be non-negative")

    # 4. evidence class vs evidence actually present
    ec = cert.get("evidence_class")
    if ec not in EVIDENCE_CLASSES:
        problems.append(
            f"evidence_class {ec!r} not one of {list(EVIDENCE_CLASSES)}")
    receipts = cert.get("run_receipts") or []
    if not isinstance(receipts, list):
        problems.append("run_receipts must be a list")
        receipts = []
    if ec == "RUNTIME_TESTED" and len(receipts) < 1:
        problems.append("RUNTIME_TESTED requires >=1 run receipt")
    if ec in ("MULTI_RUNTIME_TESTED", "ATTESTED") and len(receipts) < 2:
        problems.append(f"{ec} requires >=2 run receipts")
    if ec in ("SPEC_VALID", "STATIC_CONFORMANT") and receipts:
        problems.append(f"{ec} must not carry runtime run receipts")

    # 5. digests vs actual bytes + run-receipt references
    skill_dir = Path(args.skill) if getattr(args, "skill", None) \
        else cert_path.resolve().parent.parent
    if not (skill_dir / "SKILL.md").is_file():
        problems.append(f"skill directory not found (no SKILL.md): {skill_dir}")
    else:
        if cert.get("skill_digest") != file_digest(skill_dir / "SKILL.md"):
            problems.append("skill_digest does not match SKILL.md bytes")
        abi_p = skill_dir / "skill.abi.yaml"
        if not abi_p.is_file():
            problems.append("skill.abi.yaml missing in skill directory")
        elif cert.get("abi_digest") != file_digest(abi_p):
            problems.append("abi_digest does not match skill.abi.yaml bytes")
        lock_p = skill_dir / "skill.lock"
        if lock_p.is_file():
            if cert.get("lock_digest") != file_digest(lock_p):
                problems.append("lock_digest does not match skill.lock bytes")
        elif cert.get("lock_digest"):
            problems.append("certificate pins lock_digest but skill.lock is missing")
        for i, r in enumerate(receipts):
            if not isinstance(r, dict):
                problems.append(f"run_receipts[{i}] must be an object")
                continue
            for k in ("runtime", "harness"):
                if not r.get(k):
                    problems.append(f"run_receipts[{i}] missing {k} identifier")
            ev = r.get("evidence")
            if not ev:
                problems.append(f"run_receipts[{i}] missing evidence reference")
            elif not (skill_dir / ev).is_file():
                problems.append(f"run_receipts[{i}] evidence not found: {ev}")

    # 6. signature / bundle when signed
    if cert.get("signed") is True:
        sig = cert.get("signature")
        if not isinstance(sig, dict) or not sig:
            problems.append("signed=true requires a signature block")
        else:
            for k in ("alg", "attestor", "value"):
                if not sig.get(k):
                    problems.append(f"signature missing {k}")
            bundle = sig.get("bundle")
            if bundle and not (skill_dir / bundle).is_file():
                problems.append(f"signature bundle not found: {bundle}")
        if ec != "ATTESTED":
            problems.append("signed=true must correspond to evidence_class ATTESTED")
    elif ec == "ATTESTED":
        problems.append("ATTESTED requires signed=true")

    if problems:
        print("INVALID")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"certificate verified: {ec} ({cert.get('passed')}/{cert.get('cases')}), "
          f"digests match, {len(receipts)} run receipt(s)")
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
    p = sub.add_parser("verify-certificate"); p.add_argument("certificate"); p.add_argument("--skill", default=None); p.set_defaults(fn=cmd_verify_certificate)
    p = sub.add_parser("lock"); p.add_argument("skill"); p.set_defaults(fn=cmd_lock)
    args = ap.parse_args(raw)
    args.json = args.json or json_flag
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
