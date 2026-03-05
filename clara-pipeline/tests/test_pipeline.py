"""
Tests for the Clara Pipeline core modules.
Run with: python3 -m pytest tests/ -v
"""

import json
import sys
import os
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from utils import generate_account_id, extract_json_from_text


class TestUtils:
    """Test utility functions."""

    def test_generate_account_id_deterministic(self):
        """Same company name should always produce the same ID."""
        id1 = generate_account_id("Ben's Electric")
        id2 = generate_account_id("Ben's Electric")
        assert id1 == id2

    def test_generate_account_id_different(self):
        """Different company names produce different IDs."""
        id1 = generate_account_id("Ben's Electric")
        id2 = generate_account_id("ABC Fire Protection")
        assert id1 != id2

    def test_generate_account_id_slug_format(self):
        """Account IDs should be URL-safe slugs."""
        aid = generate_account_id("Ben's Electric Solutions")
        assert " " not in aid
        assert "'" not in aid
        assert aid.islower() or "-" in aid

    def test_extract_json_from_code_block(self):
        """Should extract JSON from markdown code blocks."""
        text = '```json\n{"name": "test", "value": 42}\n```'
        result = extract_json_from_text(text)
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_extract_json_raw(self):
        """Should extract raw JSON from text."""
        text = 'Here is the result: {"name": "test"} end'
        result = extract_json_from_text(text)
        assert result["name"] == "test"

    def test_extract_json_with_prefix(self):
        """Should handle LLM responses with text before JSON."""
        text = 'Based on the transcript, here is the extracted data:\n\n{"company_name": "Test Co"}'
        result = extract_json_from_text(text)
        assert result["company_name"] == "Test Co"


class TestPatch:
    """Test the patch/merge system."""

    def test_deep_merge_basic(self):
        from patch import deep_merge

        base = {"name": "Test", "hours": {"start": "8 AM"}}
        updates = {"hours": {"end": "5 PM"}}
        merged, changes = deep_merge(base, updates)

        assert merged["name"] == "Test"
        assert merged["hours"]["start"] == "8 AM"
        assert merged["hours"]["end"] == "5 PM"

    def test_deep_merge_override(self):
        from patch import deep_merge

        base = {"name": "Old", "phone": "111"}
        updates = {"name": "New"}
        merged, changes = deep_merge(base, updates)

        assert merged["name"] == "New"
        assert merged["phone"] == "111"
        assert len(changes) == 1
        assert changes[0]["action"] == "modified"

    def test_deep_merge_add_new(self):
        from patch import deep_merge

        base = {"name": "Test"}
        updates = {"email": "test@test.com"}
        merged, changes = deep_merge(base, updates)

        assert merged["email"] == "test@test.com"
        assert len(changes) == 1
        assert changes[0]["action"] == "added"

    def test_apply_structured_delta(self):
        from patch import apply_structured_delta

        v1 = {
            "company_name": "Test Co",
            "business_hours": {"start": None, "end": None},
            "version": "v1"
        }

        delta = {
            "changes": {
                "business_hours": {
                    "new_value": {"start": "7:30 AM", "end": "4:30 PM"},
                    "reason": "confirmed during onboarding"
                }
            },
            "new_fields": {
                "office_address": {
                    "value": "123 Main St",
                    "reason": "newly provided"
                }
            },
            "questions_or_unknowns": []
        }

        v2, changes = apply_structured_delta(v1, delta)
        assert v2["version"] == "v2"
        assert v2["office_address"] == "123 Main St"
        assert v2["business_hours"]["start"] == "7:30 AM"


class TestValidation:
    """Test schema validation."""

    def test_valid_memo(self):
        from validate import validate_memo

        memo = {
            "account_id": "test-co-abc123",
            "company_name": "Test Co",
            "version": "v1"
        }
        is_valid, errors = validate_memo(memo)
        assert is_valid

    def test_invalid_memo_missing_name(self):
        from validate import validate_memo

        memo = {
            "account_id": "test",
            "company_name": "",
            "version": "v1"
        }
        is_valid, errors = validate_memo(memo)
        assert not is_valid


class TestGenerateAgent:
    """Test agent spec generation."""

    def test_generate_basic_spec(self):
        from generate_agent import generate_agent_spec

        memo = {
            "account_id": "test-co-abc123",
            "company_name": "Test Electric",
            "business_type": "electrical",
            "business_hours": {
                "days": "Monday-Friday",
                "start": "8:00 AM",
                "end": "5:00 PM",
                "timezone": "Eastern"
            },
            "services_supported": ["electrical repair", "installations"],
            "emergency_definition": ["power outage", "electrical fire"],
            "emergency_routing_rules": {
                "primary_contact": "John",
                "primary_phone": "555-0100"
            },
            "version": "v1"
        }

        spec = generate_agent_spec(memo)
        assert spec["agent_name"] == "Clara - Test Electric"
        assert spec["version"] == "v1"
        assert "Test Electric" in spec["system_prompt"]
        assert "business hours" in spec["system_prompt"].lower()
        assert "after hours" in spec["system_prompt"].lower()
        assert "emergency" in spec["system_prompt"].lower()
