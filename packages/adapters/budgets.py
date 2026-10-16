"""Shared finite action/query/page budget; limits do not imply source completeness."""

from services.api.store import DomainError


class Budget:
    def __init__(self, limits):
        self.limits = limits
        self.queries = 0
        self.pages = 0
        self.actions = 0

    def consume(self, kind):
        if (
            self.actions >= self.limits["max_actions"]
            or kind == "query"
            and self.queries >= self.limits["max_queries"]
            or kind == "page"
            and self.pages >= self.limits["max_pages"]
        ):
            raise DomainError(
                "DISCOVERY_BUDGET_EXHAUSTED",
                "Remaining categories/sources were not retrieved within the approved workload budget.",
            )
        self.actions += 1
        if kind == "query":
            self.queries += 1
        if kind == "page":
            self.pages += 1
