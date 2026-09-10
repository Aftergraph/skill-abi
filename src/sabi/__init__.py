"""SABI — Semantic Agent Behavior Interface.

Public API surface. Every canonical operation is exposed as a
lazy-import forwarding function here.
"""
from __future__ import annotations

from sabi.errors import IntegrityError, SabiError, ValidationError

__all__ = [
    "validate_skill",
    "resolve",
    "diff",
    "bind",
    "certify",
    "verify_certificate",
    "lock",
    "verify_lock",
    "IntegrityError",
    "SabiError",
    "ValidationError",
]


def validate_skill(skill_dir, schemas_dir=None):
    from sabi.api import validate_canonical
    return validate_canonical(skill_dir, schemas_dir=schemas_dir)


def resolve(degradation, capabilities):
    from sabi.api import resolve
    return resolve(degradation, capabilities)


def diff(old, new):
    from sabi.api import diff
    return diff(old, new)


def bind(skill_dir, runtime_profile):
    from sabi.api import bind
    return bind(skill_dir, runtime_profile)


def certify(skill_dir):
    from sabi.api import certify
    return certify(skill_dir)


def verify_certificate(cert_path, skill_dir=None):
    from sabi.api import verify_certificate
    return verify_certificate(cert_path, skill_dir=skill_dir)


def lock(skill_dir):
    from sabi.api import lock
    return lock(skill_dir)


def verify_lock(skill_dir):
    from sabi.api import verify_lock
    return verify_lock(skill_dir)
