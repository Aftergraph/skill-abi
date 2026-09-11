# Historical certificates

The `portability.json` files under `examples/` and `tests/fixtures/` were
produced before certificates carried an explicit `evidence_class`. They use
the retired `certificate: "full"` label and are **retained as historical
evidence**, not rewritten in place.

They do not validate against the current `schemas/certificate.schema.json`
and MUST NOT be presented as current-class certifications. To produce a
current certificate, run:

```bash
python cli/sabi.py lock <skill>
python cli/sabi.py certify <skill>
python cli/sabi.py verify-certificate <skill>/attestations/portability.json
```

A static-only run yields `evidence_class: STATIC_CONFORMANT`; it never
claims a runtime or attested class.
