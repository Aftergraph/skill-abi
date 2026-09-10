"""Minimal JSON Schema draft 2020-12 validator for SABI (stdlib only).

Supports: type (single or list), required, properties,
additionalProperties (bool or schema), items, enum, pattern,
minimum, maximum, minItems, minLength, const, anyOf, oneOf,
and local $ref resolution against #/$defs/... within the same document.
"""
import json
import re


class SchemaValidationError(Exception):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value, tname):
    if tname == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if tname == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if tname == "boolean":
        return isinstance(value, bool)
    py = _TYPES.get(tname)
    if py is None:
        return True
    return isinstance(value, py)


def _resolve_ref(root, ref):
    if not ref.startswith("#/"):
        raise SchemaValidationError([f"unsupported $ref: {ref}"])
    node = root
    for part in ref[2:].split("/"):
        if not isinstance(node, dict):
            raise SchemaValidationError([f"unresolvable $ref: {ref}"])
        node = node.get(part)
        if node is None:
            raise SchemaValidationError([f"unresolvable $ref: {ref}"])
    return node


def validate(instance, schema, root=None, path=""):
    """Validate *instance* against a JSON Schema draft 2020-12 subset.

    Returns a list of error strings (empty means valid).
    """
    if root is None:
        root = schema
    errors = []

    if not isinstance(schema, dict):
        return errors

    # const
    if "const" in schema:
        if instance != schema["const"]:
            errors.append(f"{path or '$'}: expected const {schema['const']!r}, got {instance!r}")
            return errors

    # enum
    if "enum" in schema:
        if instance not in schema["enum"]:
            errors.append(f"{path or '$'}: value {instance!r} not in enum {schema['enum']}")
            return errors

    # type
    if "type" in schema:
        t = schema["type"]
        types = [t] if isinstance(t, str) else t
        if not any(_type_ok(instance, tn) for tn in types):
            errors.append(f"{path or '$'}: expected type {t}, got {type(instance).__name__}")
            return errors

    # numeric bounds
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance} > maximum {schema['maximum']}")

    # string constraints
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: string length {len(instance)} < minLength {schema['minLength']}")
        if "pattern" in schema:
            if not re.search(schema["pattern"], instance):
                errors.append(f"{path}: string does not match pattern {schema['pattern']!r}")

    # array constraints
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: array length {len(instance)} < minItems {schema['minItems']}")
        if "items" in schema:
            for i, item in enumerate(instance):
                errors.extend(validate(item, schema["items"], root, f"{path}[{i}]"))

    # object constraints
    if isinstance(instance, dict):
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            errors.append(
                f"{path}: object has {len(instance)} properties < minProperties {schema['minProperties']}")
        if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
            errors.append(
                f"{path}: object has {len(instance)} properties > maxProperties {schema['maxProperties']}")
        if "required" in schema:
            for key in schema["required"]:
                if key not in instance:
                    errors.append(f"{path}: missing required property '{key}'")
        props_schema = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            child_path = f"{path}.{key}" if path else key
            if key in props_schema:
                errors.extend(validate(value, props_schema[key], root, child_path))
            elif additional is False:
                errors.append(f"{child_path}: additional property not allowed")
            elif isinstance(additional, dict):
                errors.extend(validate(value, additional, root, child_path))

    # composition
    if "anyOf" in schema:
        matched = False
        for sub in schema["anyOf"]:
            e = validate(instance, sub, root, path)
            if not e:
                matched = True
                break
        if not matched:
            errors.append(f"{path or '$'}: does not match anyOf")
    if "oneOf" in schema:
        matches = sum(1 for sub in schema["oneOf"] if not validate(instance, sub, root, path))
        if matches != 1:
            errors.append(f"{path or '$'}: must match exactly one of oneOf (matched {matches})")

    # $ref
    if "$ref" in schema:
        ref_schema = _resolve_ref(root, schema["$ref"])
        errors.extend(validate(instance, ref_schema, root, path))

    return errors


def validate_json_file(filepath, schema_dict):
    """Load a JSON file and validate it. Returns (data, errors)."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data, validate(data, schema_dict)
