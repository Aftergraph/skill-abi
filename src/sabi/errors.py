"""SABI exception hierarchy mapped to CLI exit codes."""


class SabiError(Exception):
    """Base SABI error."""
    exit_code = 1


class ValidationError(SabiError):
    """Semantic validation or check failure."""
    exit_code = 1


class UsageError(SabiError):
    """CLI usage / argument error."""
    exit_code = 2


class IntegrityError(SabiError):
    """Digest mismatch, tamper detected, lock violation."""
    exit_code = 3


class SignatureError(SabiError):
    """Invalid signature or certificate verification failure."""
    exit_code = 4


class CertificationPreconditionError(SabiError):
    """Certification attempted without meeting prerequisites."""
    exit_code = 5


class DependencyError(SabiError):
    """Required dependency unresolvable."""
    exit_code = 6
