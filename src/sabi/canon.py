"""Canonical JSON serialization and sha256 digests for SABI.

Canonical form: keys sorted, compact separators, UTF-8. This is the
byte-exact representation signed over and digested.
"""
import hashlib
import json


def canonical_json(obj):
    """Return canonical JSON bytes (sorted keys, compact)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data):
    """sha256 hex digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    """sha256 hex digest of a file's bytes."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def digest_uri(data):
    """Return 'sha256:<hex>' digest URI for bytes."""
    return "sha256:" + sha256_hex(data)


def digest_file_uri(path):
    """Return 'sha256:<hex>' digest URI for a file."""
    return "sha256:" + sha256_file(path)
