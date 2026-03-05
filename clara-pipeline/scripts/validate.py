"""
JSON Schema validation for extracted account memos and agent specs.
Ensures data quality before proceeding through the pipeline.
"""

import sys
import json
import argparse
from pathlib import Path

import jsonschema
from jsonschema import validate, ValidationError

from utils import setup_logging, load_json, SCHEMAS_DIR

logger = setup_logging("validate")


def load_schema(schema_name: str) -> dict:
    """Load a JSON Schema from the schemas directory."""
    schema_path = SCHEMAS_DIR / schema_name
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    return load_json(schema_path)


def validate_memo(memo: dict) -> tuple[bool, list]:
    """
    Validate an account memo against the schema.

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    schema = load_schema("account_memo.schema.json")
    errors = []

    try:
        validate(instance=memo, schema=schema)
    except ValidationError as e:
        errors.append(f"Schema validation error: {e.message}")
        # Collect all errors
        validator = jsonschema.Draft7Validator(schema)
        for error in validator.iter_errors(memo):
            if error.message not in [e for e in errors]:
                errors.append(f"  - {error.json_path}: {error.message}")

    # Additional business logic checks
    if memo.get("company_name") in [None, "", "Unknown", "UNKNOWN"]:
        errors.append("company_name is missing or unknown")

    # Check that emergency_definition is not empty when emergency routing exists
    if memo.get("emergency_routing_rules") and not memo.get("emergency_definition"):
        errors.append("WARNING: emergency_routing_rules set but emergency_definition is empty")

    is_valid = len([e for e in errors if not e.startswith("WARNING")]) == 0
    return is_valid, errors


def validate_agent_spec(spec: dict) -> tuple[bool, list]:
    """
    Validate a Retell Agent Spec against the schema.

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    schema = load_schema("agent_spec.schema.json")
    errors = []

    try:
        validate(instance=spec, schema=schema)
    except ValidationError:
        validator = jsonschema.Draft7Validator(schema)
        for error in validator.iter_errors(spec):
            errors.append(f"  - {error.json_path}: {error.message}")

    # Check system prompt has required flow sections
    system_prompt = spec.get("system_prompt", "")
    required_sections = [
        ("business hours", "Business hours flow"),
        ("after hours", "After-hours flow"),
        ("emergency", "Emergency handling"),
        ("transfer", "Call transfer protocol"),
    ]
    for keyword, section_name in required_sections:
        if keyword.lower() not in system_prompt.lower():
            errors.append(f"WARNING: System prompt may be missing {section_name} section")

    is_valid = len([e for e in errors if not e.startswith("WARNING")]) == 0
    return is_valid, errors


def validate_file(filepath: Path, schema_type: str) -> tuple[bool, list]:
    """Validate a JSON file against its schema."""
    data = load_json(filepath)
    if schema_type == "memo":
        return validate_memo(data)
    elif schema_type == "agent_spec":
        return validate_agent_spec(data)
    else:
        return False, [f"Unknown schema type: {schema_type}"]


def main():
    parser = argparse.ArgumentParser(description="Validate JSON files against schemas")
    parser.add_argument("filepath", type=str, help="Path to JSON file")
    parser.add_argument("--type", "-t", choices=["memo", "agent_spec"], required=True,
                        help="Type of document to validate")

    args = parser.parse_args()
    filepath = Path(args.filepath)

    if not filepath.exists():
        logger.error(f"File not found: {filepath}")
        sys.exit(1)

    is_valid, errors = validate_file(filepath, args.type)

    if is_valid:
        logger.info(f"✅ Validation passed: {filepath}")
        if errors:  # warnings only
            for e in errors:
                logger.warning(e)
    else:
        logger.error(f"❌ Validation failed: {filepath}")
        for e in errors:
            logger.error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
