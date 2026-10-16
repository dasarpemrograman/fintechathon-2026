"""Local operator provisioning of pilot entitlements; does not collect payment."""

import argparse, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sqlalchemy as sa
from packages.domain.entitlements import CATALOG
from services.api import store, commands

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--organization", required=True)
p.add_argument("--plan", choices=list(CATALOG["plans"]), required=True)
p.add_argument("--expires-at")
p.add_argument("--analysis-addons", type=int, default=0)
p.add_argument("--document-addons", type=int, default=0)
p.add_argument("--addon-expires-at")
for option in ["runs", "pages", "users", "active-deals"]:
    p.add_argument("--" + option, type=int)
p.add_argument("--terms-reference")
args = p.parse_args()
overrides = {
    key: getattr(args, key.replace("-", "_"))
    for key in ["runs", "pages", "users", "active-deals"]
}
if any(value is not None and value < 0 for value in overrides.values()):
    p.error("Limits cannot be negative.")
if args.users == 0:
    p.error("A provisioned organization needs at least one user slot.")
if args.plan == "institutional" and (
    any(value is None for value in overrides.values()) or not args.terms_reference
):
    p.error(
        "Institutional provisioning requires all four explicit limits and a reviewed terms reference."
    )

if args.plan == "free_sandbox" and (args.analysis_addons or args.document_addons):
    p.error("Add-ons require an active paid entitlement.")
if min(args.analysis_addons, args.document_addons) < 0:
    p.error("Add-on quantities cannot be negative.")
now = store.now()
plan = CATALOG["plans"][args.plan]
expires = args.expires_at or (
    (now + timedelta(days=plan["duration_days"])).isoformat()
    if plan["duration_days"]
    else None
)
for timestamp in [expires, args.addon_expires_at]:
    if timestamp:
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            p.error("Expiry must be an ISO timestamp with offset.")
        if parsed.tzinfo is None:
            p.error("Expiry needs an explicit timezone offset.")
if (args.analysis_addons or args.document_addons) and not (
    args.addon_expires_at or expires
):
    p.error("Add-ons require a declared expiry date.")
with store.engine.begin() as conn:
    before = conn.execute(
        sa.select(store.organizations.c.policy)
        .where(store.organizations.c.id == args.organization)
        .with_for_update()
    ).scalar_one()
    policy = {
        **before,
        "plan": args.plan,
        "catalog_version": CATALOG["version"],
        "runs": plan["runs"],
        "pages": plan["pages"],
        "users": plan["users"],
        "active_deals": plan["active_deals"],
        "activated_at": now.isoformat(),
        "expires_at": expires,
        "active": True,
        "addons": list(before.get("addons", [])),
    }
    policy.update(
        {
            key.replace("-", "_"): value
            for key, value in overrides.items()
            if value is not None
        }
    )
    if args.terms_reference:
        policy["terms_reference"] = args.terms_reference
    for key, count in [
        ("analysis", args.analysis_addons),
        ("document", args.document_addons),
    ]:
        if count:
            addon = CATALOG["addons"][key]
            policy["addons"].append(
                {
                    "id": store.uid("addon"),
                    "unit": addon["unit"],
                    "quantity": addon["quantity"] * count,
                    "expires_at": args.addon_expires_at or expires,
                }
            )
    conn.execute(
        store.organizations.update()
        .where(store.organizations.c.id == args.organization)
        .values(policy=policy)
    )
    commands.audit(
        conn,
        {
            "tenant": args.organization,
            "actor": "local_operator",
            "scope": "real",
            "request_id": store.uid("request"),
        },
        "provisionPilotEntitlement",
        before,
        policy,
    )
print(
    "Pilot entitlement provisioned. No payment, checkout or automatic overage occurred."
)
