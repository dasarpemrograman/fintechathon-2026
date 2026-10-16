"""Non-destructive migration of pre-runtime immutable snapshots."""

from copy import deepcopy


def import_snapshot(original: dict, *, resource: str) -> tuple[dict, dict]:
    """Return preserved original and a separately versioned 2.2 projection.

    A migrated record has no demo authority. Missing invoices are not silently
    treated as zero revenue: their absence is an explicit calculation blocker.
    """
    if resource not in {"workspace", "deal"}:
        raise ValueError("Only workspace/deal snapshots can be imported")
    if original.get("schema_version") != "2.1":
        raise ValueError("Expected a 2.1 source snapshot")
    preserved = deepcopy(original)
    migrated = deepcopy(original)
    migrated.update(
        schema_version="2.2", execution_scope="real", dataset_id=None, archived=False
    )
    if resource == "deal":
        migrated["invoices"] = []
        migrated.setdefault("unknowns", []).append(
            {
                "field_path": "/invoices",
                "status": "missing",
                "reason": "Draft 2.1 did not declare invoice totals; review the original contract before calculation.",
            }
        )
    return preserved, migrated
