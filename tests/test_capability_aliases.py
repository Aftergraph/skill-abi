import json
from pathlib import Path

from sabi import vocab


ROOT = Path(__file__).resolve().parents[1]


def test_capability_alias_registry_is_collision_free_and_canonical():
    doc = json.loads((ROOT / "spec" / "capability-aliases-v0.1.json").read_text(encoding="utf-8"))
    assert doc["schema_version"] == "sabi-capability-aliases/v0.1"

    seen = {}
    for entry in doc["entries"]:
        canonical = entry["canonical"]
        assert vocab.is_known(canonical), canonical
        for alias in entry["aliases"]:
            normalized = alias.strip().lower().replace("_", ".").replace(" ", ".")
            prior = seen.get(normalized)
            assert prior in (None, canonical), f"alias collision: {alias} -> {prior}, {canonical}"
            seen[normalized] = canonical


def test_alias_registry_does_not_create_new_authority_semantics():
    doc = json.loads((ROOT / "spec" / "capability-aliases-v0.1.json").read_text(encoding="utf-8"))
    for entry in doc["entries"]:
        assert entry["canonical"] in vocab.VOCAB
