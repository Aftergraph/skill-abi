"""SABI — Skill ABI reference implementation.

Machine-verifiable contract for portable agent skills.
"""
__version__ = "0.1.0"

from sabi.errors import (
    SabiError,
    ValidationError,
    UsageError,
    IntegrityError,
    SignatureError,
    CertificationPreconditionError,
    DependencyError,
)

__all__ = [
    "__version__",
    "SabiError",
    "ValidationError",
    "UsageError",
    "IntegrityError",
    "SignatureError",
    "CertificationPreconditionError",
    "DependencyError",
]
