"""Repository that maps NodeModel rows to/from the Node domain entity."""

from iam.domain.entities import Node
from iam.infrastructure.models import NodeModel


class NodeRepository:
    def find_by_device_id(self, device_id):
        row = NodeModel.get_or_none(NodeModel.device_id == device_id)
        if row is None:
            return None
        return Node(row.device_id, row.api_key, row.label)

    def create(self, node):
        NodeModel.create(device_id=node.device_id, api_key=node.api_key, label=node.label)
        return node
