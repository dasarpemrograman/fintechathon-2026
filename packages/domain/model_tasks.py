"""Bounded model suggestions: schema validation and reference containment before use."""

from jsonschema import ValidationError
from packages.contracts.runtime import DOCUMENT
from scripts.validate_contract import schema_validator
from packages.adapters.providers import model_task
from services.api.store import DomainError


def validate_selection(value, evidence_ids):
    try:
        schema_validator(DOCUMENT, "ModelSectionSelection").validate(value)
    except ValidationError:
        raise DomainError(
            "MODEL_INVALID_OUTPUT",
            "Model suggestion failed its task-specific canonical schema.",
        )
    if not set(value["evidence_ids"]) <= set(evidence_ids):
        raise DomainError(
            "MODEL_INVENTED_REFERENCE",
            "Model suggested a source outside this immutable input set.",
        )
    return value


def explain(analysis, evidence_ids, live=False, record_receipt=None):
    if not live:
        return {
            "sections": ["overview", "costs", "cash", "risks"],
            "metric_keys": [
                "contribution",
                "seller_operating_expense",
                "minimum_cash",
                "buffer_shortfall",
                "final_cash",
            ],
            "evidence_ids": evidence_ids[:30],
        }
    payload = {
        "completeness": analysis["completeness"],
        "blocker_codes": [i["code"] for i in analysis["blockers"]],
        "allowed_evidence_ids": evidence_ids[:30],
        "allowed_sections": ["overview", "costs", "cash", "risks"],
        "allowed_metric_keys": [
            "contribution",
            "seller_operating_expense",
            "minimum_cash",
            "buffer_shortfall",
            "final_cash",
        ],
    }
    for attempt in range(2):
        try:
            response = model_task("select_explanation_sections", payload)
        except DomainError as error:
            if record_receipt and getattr(error, "provider_receipt", None):
                record_receipt(error.provider_receipt)
            raise
        try:
            selected = validate_selection(response["data"], evidence_ids)
            if record_receipt:
                record_receipt(response)
            return selected
        except DomainError:
            if record_receipt:
                record_receipt(
                    {
                        **response,
                        "status": "invalid_response",
                        "limitations": [
                            "Task schema or reference containment failed; no suggestion was applied."
                        ],
                    }
                )
            if attempt:
                raise
            payload["repair_instruction"] = (
                "Return only sections, metric_keys, evidence_ids from the supplied allowlists; no extra fields."
            )
    raise DomainError(
        "MODEL_INVALID_OUTPUT", "Model could not produce a valid bounded suggestion."
    )
