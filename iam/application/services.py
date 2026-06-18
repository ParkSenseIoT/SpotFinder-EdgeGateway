"""IAM application service: device registry + authentication use cases."""

from iam.domain.entities import Node
from iam.domain.services import NodeAuthService
from iam.infrastructure.repositories import NodeRepository

# Hard-coded dev credentials (local development only — do NOT use in production).
TEST_NODE_ID = "spotfinder-node-001"
TEST_NODE_API_KEY = "test-api-key-123"


class AuthApplicationService:
    def __init__(self):
        self.nodes = NodeRepository()

    def get_or_create_test_node(self):
        node = self.nodes.find_by_device_id(TEST_NODE_ID)
        if node is None:
            node = self.nodes.create(Node(TEST_NODE_ID, TEST_NODE_API_KEY, "Dev test node"))
        return node

    def authenticate(self, device_id, api_key):
        node = self.nodes.find_by_device_id(device_id)
        return NodeAuthService.matches(node, api_key)
