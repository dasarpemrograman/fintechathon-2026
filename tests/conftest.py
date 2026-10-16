"""Record operation/status coverage from real HTTP handlers, without payloads."""

from collections import Counter
from pathlib import Path
import json
from services.api.app import app
from packages.contracts.runtime import OPERATIONS

observed = Counter()


@app.middleware("http")
async def observe_contract_operations(request, call_next):
    response = await call_next(request)
    route = request.scope.get("route")
    if route and route.name in OPERATIONS:
        observed[(route.name, response.status_code)] += 1
    return response


def pytest_sessionfinish(session, exitstatus):
    result = {
        name: {
            "method": method,
            "statuses": {
                str(status): count
                for (operation, status), count in sorted(observed.items())
                if operation == name
            },
        }
        for name, (_, method, _) in OPERATIONS.items()
    }
    target = Path(".local/operation-coverage.json")
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n")
    target.chmod(0o600)
