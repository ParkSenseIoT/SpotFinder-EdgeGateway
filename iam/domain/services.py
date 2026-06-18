"""IAM domain services (pure business rules, no framework)."""


class NodeAuthService:
    """Decides whether a presented API key matches a registered node."""

    @staticmethod
    def matches(node, api_key):
        return node is not None and api_key is not None and node.api_key == api_key
