"""Quantified effect-envelope semantics (SABI E module).

Three pure, provider-neutral operations:

* :func:`validate_envelope` — is a declared envelope well-formed and typed?
* :func:`envelope_contains` — does one envelope stay inside another (no widening)?
* :func:`check_observed`   — does an observed effect record stay inside its envelope?

SABI defines the **semantic bound** only. These functions decide what a
declared envelope means and whether one envelope is contained in another;
they never block, throttle, retry, or talk to a provider. Runtime and trust
systems are responsible for *enforcing* the bound at execution time.

Widening is always rejected: an inner envelope that declares authority
beyond the outer (declared) envelope yields violations. Undeclared
dimensions default to empty (no access), never to unlimited, so an inner
envelope that omits a dimension the outer bounds is contained; an inner
envelope that exceeds it is not.
"""
from __future__ import annotations

import fnmatch
import re
from typing import Dict, Iterable, List, Tuple

# --- canonical categories (v0.2) -------------------------------------------

CATEGORIES = (
    "filesystem",
    "repository",
    "process",
    "network",
    "message",
    "artifact",
    "deployment",
    "credential",
    "money",
)

# v0.1 dotted names remain valid and map onto the canonical categories.
ALIASES = {
    "filesystem.read": "filesystem",
    "filesystem.write": "filesystem",
    "repository.push": "repository",
    "repository.write": "repository",
    "process.spawn": "process",
    "network.egress": "network",
    "message.send": "message",
    "artifact.create": "artifact",
    "deployment.create": "deployment",
    "credentials": "credential",
}

# Constraint keys that apply to each category. Anything else is a typing error.
CONSTRAINTS = {
    "filesystem": ("allowed", "scope", "paths", "max_operations"),
    "repository": ("allowed", "scope", "branches", "max_operations"),
    "process": ("allowed", "scope", "environment", "max_operations"),
    "network": ("allowed", "destinations", "domains", "max_operations"),
    "message": ("allowed", "destinations", "max_operations"),
    "artifact": ("allowed", "scope", "paths", "max_operations"),
    "deployment": ("allowed", "scope", "destinations", "environment", "max_operations"),
    "credential": ("allowed", "scope", "environment", "expose_to_model", "max_operations"),
    "money": ("allowed", "amount", "max_amount", "currency", "max_operations"),
}

# Free-text documentation is permitted on every category; it never widens a bound.
NOTE_KEY = "note"

LIST_CONSTRAINTS = ("scope", "paths", "branches", "destinations", "domains", "environment")

# Observed-record keys -> envelope keys that bound them.
OBSERVED_LISTS = {
    "filesystem": {"paths": ("paths", "scope")},
    "artifact": {"paths": ("paths", "scope")},
    "repository": {"branches": ("branches", "scope")},
    "process": {"scope": ("scope",), "environment": ("environment",)},
    "network": {"domains": ("domains",), "destinations": ("destinations",)},
    "message": {"destinations": ("destinations",)},
    "deployment": {"destinations": ("destinations",), "environment": ("environment",)},
    "credential": {"scope": ("scope",), "environment": ("environment",)},
}

_NOUN = {
    "paths": "path",
    "branches": "branch",
    "destinations": "destination",
    "domains": "domain",
    "scope": "scope",
    "environment": "environment",
}

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


# --- helpers ---------------------------------------------------------------

def canonical_category(name: str):
    """Return the canonical category for *name*, or ``None`` if unknown."""
    if name in CATEGORIES:
        return name
    return ALIASES.get(name)


def _is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _bound(value) -> float:
    """Numeric bound, defaulting to 0 (undeclared == no access)."""
    return value if _is_num(value) and value >= 0 else 0


def _is_vacuous(spec) -> bool:
    """True when a declaration grants no authority at all."""
    if not isinstance(spec, dict) or not spec:
        return True
    if spec.get("allowed") is True or spec.get("expose_to_model") is True:
        return False
    if _bound(spec.get("max_operations")) > 0:
        return False
    if _bound(spec.get("amount", spec.get("max_amount"))) > 0:
        return False
    return not any(spec.get(key) for key in LIST_CONSTRAINTS)


def _allowed(spec) -> bool:
    """Effective ``allowed``: explicit flag wins, else implied by the bounds."""
    flag = spec.get("allowed")
    if isinstance(flag, bool):
        return flag
    return not _is_vacuous(spec)


def _declares_bound(spec) -> bool:
    if any(key in spec for key in ("max_operations", "amount", "max_amount", "expose_to_model")):
        return True
    return any(spec.get(key) for key in LIST_CONSTRAINTS)


def _glob_covers(outer: str, inner: str) -> bool:
    """True when the *outer* glob provably covers the *inner* pattern or value.

    Conservative by construction: an inner pattern is only covered when the
    outer pattern cannot be narrower. Anything the algorithm cannot prove is
    treated as widening and rejected.
    """
    if outer == inner:
        return True
    if outer.endswith("/**"):
        prefix = outer[:-3].rstrip("/")
        return inner == prefix or inner.startswith(prefix + "/") or inner == prefix + "/**"
    if outer.endswith("*"):
        prefix = outer[:-1]
        if not inner.startswith(prefix):
            return False
        return "/" not in inner[len(prefix):]
    # Literal outer covers only an identical literal inner.
    if any(ch in inner for ch in "*?["):
        return False
    return fnmatch.fnmatch(inner, outer)


def _covered(value: str, patterns: Iterable[str], workspace: str = "") -> bool:
    for pat in patterns or []:
        if not isinstance(pat, str):
            continue
        pat = pat.replace("${workspace}", workspace or "")
        candidate = value.replace("${workspace}", workspace or "") if isinstance(value, str) else value
        if isinstance(candidate, str) and _glob_covers(pat, candidate):
            return True
    return False


def _normalize(envelope) -> Tuple[Dict[str, dict], List[str]]:
    """Canonicalise an envelope; returns (mapping, errors)."""
    out: Dict[str, dict] = {}
    errors: List[str] = []
    if envelope is None:
        return out, errors
    if not isinstance(envelope, dict):
        return out, ["envelope must be a mapping of effect categories"]
    for name, spec in envelope.items():
        cat = canonical_category(name)
        if cat is None:
            errors.append(f"unknown effect category {name!r}")
            continue
        if cat in out:
            errors.append(f"duplicate effect category {name!r} (canonical {cat!r})")
            continue
        out[cat] = spec if isinstance(spec, dict) else {}
    return out, errors


# --- semantic validation of a declared envelope ----------------------------

def validate_envelope(envelope) -> List[str]:
    """Return typing/quantification errors for a declared envelope.

    Empty list means the envelope is a well-formed semantic bound. This is a
    pure shape/semantics check: it does not decide whether the bound is
    acceptable, only whether it is expressible and quantified.
    """
    errors: List[str] = []
    if not isinstance(envelope, dict) or not envelope:
        return ["envelope must be a non-empty mapping of effect categories"]

    seen = set()
    for name, spec in envelope.items():
        cat = canonical_category(name)
        if cat is None:
            errors.append(f"unknown effect category {name!r}")
            continue
        if cat in seen:
            errors.append(f"duplicate effect category {name!r} (canonical {cat!r})")
            continue
        seen.add(cat)

        if not isinstance(spec, dict) or not spec:
            errors.append(f"effect {name!r} must be a non-empty quantified mapping")
            continue

        applicable = CONSTRAINTS[cat] + (NOTE_KEY,)
        for key in spec:
            if key not in applicable:
                errors.append(
                    f"constraint {key!r} is not applicable to effect category {cat!r}"
                )

        if "allowed" in spec and not isinstance(spec["allowed"], bool):
            errors.append(f"{cat}.allowed must be a boolean")

        if "max_operations" in spec:
            mo = spec["max_operations"]
            if not (isinstance(mo, int) and not isinstance(mo, bool) and mo >= 0):
                errors.append(f"{cat}.max_operations must be a non-negative integer")

        for key in LIST_CONSTRAINTS:
            if key not in spec:
                continue
            value = spec[key]
            if not isinstance(value, list):
                errors.append(f"{cat}.{key} must be a list of non-empty strings")
                continue
            for item in value:
                if not isinstance(item, str) or not item:
                    errors.append(f"{cat}.{key} entries must be non-empty strings")

        if cat == "credential":
            expose = spec.get("expose_to_model")
            if expose is not None and not isinstance(expose, bool):
                errors.append("credential.expose_to_model must be a boolean")

        if cat == "money":
            amount = spec.get("amount", spec.get("max_amount"))
            if amount is not None and not (_is_num(amount) and amount >= 0):
                errors.append("money.amount must be a non-negative number")
            currency = spec.get("currency")
            if currency is not None and not (
                isinstance(currency, str) and _CURRENCY_RE.match(currency)
            ):
                errors.append("money.currency must be a 3-letter uppercase ISO 4217 code")
            if _bound(amount) > 0 and currency is None:
                errors.append("money.amount greater than 0 requires an explicit currency")

        if spec.get("allowed") is True and not _declares_bound(spec):
            errors.append(
                f"{cat}: allowed is true but no quantified bound is declared"
            )
        if spec.get("allowed") is False and not _is_vacuous(spec):
            errors.append(
                f"{cat}: allowed is false but the envelope declares non-empty bounds"
            )
    return errors


# --- containment: widening is rejected -------------------------------------

def envelope_contains(outer, inner, workspace: str = "") -> List[str]:
    """Return violations where *inner* widens beyond *outer*.

    Empty list means ``inner ⊆ outer``. Every dimension is compared
    conservatively: undeclared outer dimensions are empty (0), list entries
    must be glob-covered, money must not grow, and the currency must match.
    """
    errors: List[str] = []
    o, oe = _normalize(outer)
    i, ie = _normalize(inner)
    errors.extend(oe)
    errors.extend(ie)

    for cat, ispec in i.items():
        if _is_vacuous(ispec):
            continue
        ospec = o.get(cat)
        if ospec is None:
            errors.append(
                f"widening: effect category {cat!r} is not declared in the outer envelope"
            )
            continue

        if _allowed(ispec) and not _allowed(ospec):
            errors.append(f"widening: {cat}.allowed exceeds outer envelope")

        imax = _bound(ispec.get("max_operations"))
        omax = _bound(ospec.get("max_operations"))
        if imax > omax:
            errors.append(
                f"widening: {cat}.max_operations {imax} exceeds outer envelope {omax}"
            )

        for key in LIST_CONSTRAINTS:
            if key not in CONSTRAINTS[cat]:
                continue
            for entry in ispec.get(key) or []:
                if not _covered(entry, ospec.get(key) or [], workspace):
                    errors.append(
                        f"widening: {cat}.{key} entry {entry!r} outside outer envelope"
                    )

        if cat == "credential" and ispec.get("expose_to_model") is True \
                and ospec.get("expose_to_model") is not True:
            errors.append("widening: credential.expose_to_model exceeds outer envelope")

        if cat == "money":
            iamt = _bound(ispec.get("amount", ispec.get("max_amount")))
            oamt = _bound(ospec.get("amount", ospec.get("max_amount")))
            if iamt > oamt:
                errors.append(
                    f"widening: money.amount {iamt} exceeds outer envelope {oamt}"
                )
            ic = ispec.get("currency")
            oc = ospec.get("currency")
            if iamt > 0 and ic != oc:
                errors.append(
                    f"widening: money.currency {ic!r} differs from outer envelope {oc!r}"
                )
    return errors


# --- observed-effect containment -------------------------------------------

def check_observed(envelope: Dict, observed: Dict, workspace: str = "") -> List[str]:
    """Check one observed-effects mapping against the envelope.

    Never invents effects: undeclared-but-zero observations are clean;
    undeclared non-zero observations are violations.
    """
    errors: List[str] = []
    env, _ = _normalize(envelope)
    obs = observed or {}

    if obs.get("credentials_exposed"):
        errors.append("credential exposure violates envelope")

    for name, record in obs.items():
        if name == "credentials_exposed":
            continue
        cat = canonical_category(name)
        if cat is None:
            errors.append(f"unknown observed effect category {name!r}")
            continue
        if not isinstance(record, dict):
            continue

        observed_lists = OBSERVED_LISTS.get(cat, {})
        amount = record.get("amount")
        active = bool(record.get("count", 0)) or _bound(amount) > 0 or any(
            record.get(key) for key in observed_lists
        ) or record.get("expose_to_model") is True

        es = env.get(cat)
        if es is None:
            if active:
                errors.append(f"{name} observed but no envelope entry")
            continue
        if not _allowed(es) and active:
            errors.append(f"{name} observed but envelope does not allow {cat}")
            continue

        if _bound(record.get("count", 0)) > _bound(es.get("max_operations")):
            errors.append(f"{name} count exceeds envelope")

        for key, envelope_keys in observed_lists.items():
            patterns: List[str] = []
            for envelope_key in envelope_keys:
                patterns.extend(es.get(envelope_key) or [])
            for item in record.get(key) or []:
                if not _covered(item, patterns, workspace):
                    noun = _NOUN.get(key, key)
                    suffix = "outside envelope scope" if cat == "filesystem" else "outside envelope"
                    errors.append(f"{name} {noun} {item!r} {suffix}")

        if cat == "money":
            if _bound(amount) > _bound(es.get("amount", es.get("max_amount"))):
                errors.append(f"{name} amount exceeds envelope")
            currency = record.get("currency")
            if currency is not None and currency != es.get("currency"):
                errors.append(f"{name} currency {currency!r} outside envelope")

        if cat == "credential" and record.get("expose_to_model") is True \
                and es.get("expose_to_model") is not True:
            errors.append("credential exposure violates envelope")

    return errors
