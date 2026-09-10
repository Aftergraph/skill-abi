"""Semantic validation of a SABI skill directory (levels P0-P3 + lock).

Pure checks over an already-parsed Manifest plus the files in the
skill directory. No network, no LLM. All findings are accumulated as
strings and returned; callers raise/map to ValidationError as needed.
"""
import json
from pathlib import Path

from sabi import schema as json_schema
from sabi import vocab
from sabi.errors import ValidationError
from sabi.parser import load_manifest, parse_abi_yaml
from sabi.lockfile import check_lock


def validate_skill(skill_dir, schemas_dir=None, write_lock=False):
    """Validate one skill directory. Returns (level, errors).

    level is the highest conformance level proven (P0, P1, P2, P3),
    or a failure marker. errors is a list of finding strings.
    """
    skill_dir = Path(skill_dir)
    errors = []
    level = "INVALID"

    # --- P0: parseable contract ---
    try:
        manifest = load_manifest(skill_dir)
    except ValidationError as exc:
        errors.append(f"P0: {exc}")
        return level, errors

    skill_md = skill_dir / "SKILL.md"
    body = skill_md.read_text(encoding="utf-8")
    # body must be non-empty after frontmatter
    idx = body.find("\n---")
    rest = body[idx + 4:] if idx >= 0 else ""
    if not rest.strip():
        errors.append("P0: empty body after frontmatter")

    if manifest.name != skill_dir.name:
        errors.append(
            f"P0: frontmatter name {manifest.name!r} != directory {skill_dir.name!r}")

    # schema-validate the frontmatter itself when a schema dir is given
    if schemas_dir is not None:
        fm_schema = _load_schema(Path(schemas_dir) / "skill-md.schema.json")
        if fm_schema is not None:
            for msg in json_schema.validate(manifest.raw_frontmatter, fm_schema):
                errors.append(f"P0: frontmatter schema: {msg}")

    # Agent Skills frontmatter rules (name format, description length, etc.)
    from sabi.parser import validate_agent_skills_frontmatter
    for msg in validate_agent_skills_frontmatter(manifest.raw_frontmatter):
        errors.append(f"P0: agent-skills: {msg}")

    p0_ok = not errors
    if p0_ok:
        level = "P0"

    # --- P1: spec-valid ABI ---
    abi_path = skill_dir / "skill.abi.yaml"
    if not abi_path.is_file():
        errors.append("P1: skill.abi.yaml missing")
        return level, errors
    abi = parse_abi_yaml(abi_path)

    spec = str(abi.get("spec", ""))
    if not spec.startswith("sabi/"):
        errors.append("P1: abi spec must look like sabi/vX")

    for key in ("required", "optional"):
        caps = (abi.get("capabilities", {}) or {}).get(key, []) or []
        for bad in vocab.unknown(caps):
            errors.append(f"P1: capability {bad!r} not in SABI vocabulary")

    # inputs/outputs schemas referenced must exist, parse, and validate
    for ref in ("inputs", "outputs"):
        rel = (abi.get(ref, {}) or {}).get("schema")
        if not rel:
            errors.append(f"P1: abi {ref}.schema missing")
            continue
        sp = skill_dir / rel
        if not sp.is_file():
            errors.append(f"P1: schema file {rel} missing")
            continue
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"P1: {rel} is not valid JSON: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"P1: {rel} must be a JSON object")
            continue
        sd = _load_schema(Path(schemas_dir) / "abi.schema.json") if schemas_dir else None
        if sd is not None:
            # Validate the ABI yaml document against the abi schema.
            for msg in json_schema.validate(abi, sd):
                errors.append(f"P1: abi schema: {msg}")

    if not errors:
        level = "P1"

    # --- P2: effect-aware ---
    eff_path = skill_dir / "effects.yaml"
    if not eff_path.is_file():
        errors.append("P2: effects.yaml missing")
        return level, errors
    try:
        import yaml
        eff_doc = yaml.safe_load(eff_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        errors.append(f"P2: effects.yaml YAML error: {exc}")
        return level, errors
    effects = eff_doc.get("effects")
    if not isinstance(effects, dict) or not effects:
        errors.append("P2: effects.yaml needs a non-empty effects mapping")
        return level, errors
    for name, spec in effects.items():
        if not isinstance(spec, dict) or not spec:
            errors.append(f"P2: effect {name!r} must be a quantified mapping")
    creds = effects.get("credentials", {})
    if isinstance(creds, dict) and creds.get("expose_to_model") is not False:
        errors.append("P2: credentials.expose_to_model must be explicitly false")
    if schemas_dir is not None:
        es = _load_schema(Path(schemas_dir) / "effects.schema.json")
        if es is not None:
            for msg in json_schema.validate(eff_doc, es):
                errors.append(f"P2: effects schema: {msg}")

    if not errors:
        level = "P2"

    # --- P3: degradation-conformant ---
    deg_path = skill_dir / "degradation.yaml"
    if not deg_path.is_file():
        errors.append("P3: degradation.yaml missing")
        return level, errors
    try:
        import yaml
        deg_doc = yaml.safe_load(deg_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        errors.append(f"P3: degradation.yaml YAML error: {exc}")
        return level, errors
    tiers = deg_doc.get("degradation")
    if not isinstance(tiers, dict) or len(tiers) < 2:
        errors.append("P3: degradation needs at least 2 tiers")
        return level, errors
    names = list(tiers.keys())
    last = tiers[names[-1]]
    if not isinstance(last, dict) or last.get("terminal") is not True:
        errors.append("P3: last tier must be terminal: true")
    for name in names[:-1]:
        req = (tiers[name] or {}).get("requires", [])
        if not isinstance(req, list):
            errors.append(f"P3: tier {name!r} requires must be a list")
            continue
        for bad in vocab.unknown(req):
            errors.append(f"P3: tier {name!r} capability {bad!r} not in vocabulary")
    required = (abi.get("capabilities", {}) or {}).get("required", []) or []
    first_req = set((tiers[names[0]] or {}).get("requires", []) or [])
    missing = set(required) - first_req
    if missing:
        errors.append(f"P3: full tier must cover ABI required caps, missing {sorted(missing)}")
    if schemas_dir is not None:
        ds = _load_schema(Path(schemas_dir) / "degradation.schema.json")
        if ds is not None:
            for msg in json_schema.validate(deg_doc, ds):
                errors.append(f"P3: degradation schema: {msg}")

    # --- lock ---
    lock_ok, lock_errors = check_lock(skill_dir, write_lock=write_lock)
    errors.extend(lock_errors)

    if not errors:
        level = "P3"
    return level, errors


def _load_schema(path):
    path = Path(path)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None