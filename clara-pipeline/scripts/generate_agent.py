"""
Generate Retell Agent Spec JSON from an Account Memo.
Fills the agent prompt template with memo data and produces a deployable spec.
"""

import sys
import json
import argparse
from pathlib import Path

from jinja2 import Template

from utils import (
    setup_logging, load_json, load_text, save_json, get_timestamp,
    PROMPTS_DIR
)

logger = setup_logging("generate_agent")


def build_system_prompt(memo: dict) -> str:
    """
    Generate the agent's system prompt by filling the template with memo data.

    Args:
        memo: Account Memo JSON dict

    Returns:
        Filled system prompt string
    """
    template_text = load_text(PROMPTS_DIR / "agent_prompt_template.txt")
    template = Template(template_text)

    # Prepare template variables
    bh = memo.get("business_hours") or {}
    er = memo.get("emergency_routing_rules") or {}
    ner = memo.get("non_emergency_routing_rules") or {}
    ctr = memo.get("call_transfer_rules") or {}

    # Build services list
    services = memo.get("services_supported") or []
    services_list = "\n".join(f"- {s}" for s in services) if services else "- General services"

    # Build emergency definition list
    emergencies = memo.get("emergency_definition") or []
    emergency_def_list = "\n".join(f"- {e}" for e in emergencies) if emergencies else "- As determined by the caller's urgency"

    # Build emergency routing instructions
    escalation = er.get("escalation_order") or []
    if escalation:
        routing_lines = []
        for i, contact in enumerate(escalation, 1):
            routing_lines.append(f"   {i}. Try: {contact}")
        emergency_routing = "\n".join(routing_lines)
    elif er.get("primary_phone"):
        emergency_routing = f"   1. Try: {er.get('primary_contact', 'On-call')} at {er['primary_phone']}"
        if er.get("secondary_phone"):
            emergency_routing += f"\n   2. Try: {er.get('secondary_contact', 'Backup')} at {er['secondary_phone']}"
    else:
        emergency_routing = "   Attempt to reach the on-call team member."

    # Build office hours routing
    if ner.get("route_to"):
        office_routing = f"   Transfer caller to: {ner['route_to']}"
        if ner.get("action"):
            office_routing += f"\n   Action: {ner['action']}"
    else:
        office_routing = "   Transfer to the main office line or take a message."

    # Build transfer rules
    timeout = ctr.get("timeout_seconds", 30)
    retries = ctr.get("max_retries", 2)
    transfer_rules = f"- Attempt transfer for up to {timeout} seconds\n- Maximum {retries} retry attempts"
    if ctr.get("failure_action"):
        transfer_rules += f"\n- On failure: {ctr['failure_action']}"

    # Build transfer fail protocol
    fail_msg = ctr.get("failure_message", "I'm sorry, I wasn't able to connect you directly.")
    fail_action = ctr.get("failure_action", "I'll make sure your message is passed along to the team right away.")
    transfer_fail = f'Say: "{fail_msg} {fail_action}"'

    # Emergency transfer fail
    emergency_fail = er.get("fallback_action", "Take detailed message and assure urgent follow-up.")
    emergency_transfer_fail = f'"{fail_msg} This is marked as urgent - {emergency_fail}"'

    # Build integration constraints
    constraints = memo.get("integration_constraints") or []
    integration_text = "\n".join(f"- {c}" for c in constraints) if constraints else "- No special integration constraints documented."

    # Build fallback protocol
    fallback = f"- Say: \"{fail_msg}\"\n- Action: {fail_action}"

    prompt = template.render(
        company_name=memo.get("company_name", "the company"),
        business_type=memo.get("business_type", "service company"),
        office_address=memo.get("office_address", "Address not provided"),
        timezone=bh.get("timezone", "local time"),
        business_hours_days=bh.get("days", "Monday-Friday"),
        business_hours_start=bh.get("start", "8:00 AM"),
        business_hours_end=bh.get("end", "5:00 PM"),
        services_list=services_list,
        office_hours_routing=office_routing,
        emergency_definition="\n".join(f"     - {e}" for e in emergencies) if emergencies else "     - Caller states it is an emergency",
        emergency_routing=emergency_routing,
        emergency_definition_list=emergency_def_list,
        call_transfer_rules=transfer_rules,
        transfer_fail_protocol=transfer_fail,
        emergency_transfer_fail=emergency_transfer_fail,
        fallback_protocol=fallback,
        integration_constraints=integration_text,
    )

    return prompt


def generate_agent_spec(memo: dict) -> dict:
    """
    Generate a complete Retell Agent Spec from an Account Memo.

    Args:
        memo: Account Memo JSON dict

    Returns:
        Retell Agent Spec JSON dict
    """
    system_prompt = build_system_prompt(memo)

    bh = memo.get("business_hours") or {}
    er = memo.get("emergency_routing_rules") or {}
    version = memo.get("version", "v1")

    # Build transfer targets
    transfer_targets = []
    if er.get("primary_phone"):
        transfer_targets.append({
            "name": er.get("primary_contact", "Primary Contact"),
            "phone": er["primary_phone"],
            "priority": 1,
            "conditions": "emergency"
        })
    if er.get("secondary_phone"):
        transfer_targets.append({
            "name": er.get("secondary_contact", "Secondary Contact"),
            "phone": er["secondary_phone"],
            "priority": 2,
            "conditions": "emergency_fallback"
        })

    # Build tool invocations (placeholders - not visible to caller)
    tool_invocations = [
        {
            "name": "transfer_call",
            "description": "Transfer the active call to a specified phone number",
            "trigger": "When routing to a specific contact is needed",
            "parameters": {"phone_number": "string", "caller_info": "object"}
        },
        {
            "name": "create_ticket",
            "description": "Create a service ticket/message for follow-up",
            "trigger": "When transfer fails or message needs to be logged",
            "parameters": {
                "caller_name": "string",
                "phone": "string",
                "message": "string",
                "priority": "string",
                "is_emergency": "boolean"
            }
        },
        {
            "name": "check_business_hours",
            "description": "Determine if current time is within business hours",
            "trigger": "At call start to determine flow",
            "parameters": {"timezone": "string"}
        }
    ]

    ctr = memo.get("call_transfer_rules") or {}

    spec = {
        "agent_name": f"Clara - {memo.get('company_name', 'Unknown')}",
        "version": version,
        "voice_style": {
            "voice_id": "eleven_professional",
            "style": "professional, warm, calm, empathetic",
            "language": "en-US"
        },
        "system_prompt": system_prompt,
        "key_variables": {
            "company_name": memo.get("company_name"),
            "timezone": bh.get("timezone"),
            "business_hours": f"{bh.get('days', 'Mon-Fri')} {bh.get('start', '8AM')}-{bh.get('end', '5PM')}",
            "office_address": memo.get("office_address"),
            "emergency_contacts": er.get("escalation_order") or [
                f"{er.get('primary_contact', 'N/A')}: {er.get('primary_phone', 'N/A')}"
            ]
        },
        "tool_invocations": tool_invocations,
        "call_transfer_protocol": {
            "enabled": bool(transfer_targets),
            "targets": transfer_targets,
            "timeout_seconds": ctr.get("timeout_seconds", 30),
            "max_retries": ctr.get("max_retries", 2)
        },
        "fallback_protocol": {
            "transfer_fail_message": ctr.get("failure_message",
                "I'm sorry, I wasn't able to connect you directly. Let me take your information and have someone call you back as soon as possible."),
            "transfer_fail_action": ctr.get("failure_action",
                "Collect caller details and create urgent follow-up ticket"),
            "general_error_message": "I apologize for any inconvenience. Let me take your details to ensure you get a callback."
        },
        "metadata": {
            "account_id": memo.get("account_id"),
            "created_at": get_timestamp(),
            "updated_at": None,
            "source": f"{version}_generation"
        }
    }

    logger.info(f"Generated agent spec: {spec['agent_name']} ({version})")
    return spec


def main():
    parser = argparse.ArgumentParser(description="Generate Retell Agent Spec from Account Memo")
    parser.add_argument("memo_path", type=str, help="Path to Account Memo JSON")
    parser.add_argument("--output", "-o", type=str, help="Output path for agent spec")

    args = parser.parse_args()
    memo_path = Path(args.memo_path)

    if not memo_path.exists():
        logger.error(f"Memo not found: {memo_path}")
        sys.exit(1)

    memo = load_json(memo_path)
    spec = generate_agent_spec(memo)

    if args.output:
        save_json(spec, Path(args.output))
    else:
        print(json.dumps(spec, indent=2))


if __name__ == "__main__":
    main()
