"""IAM domain entities."""


class Node:
    """An IoT node identified by its device id.

    In SpotFinder a node is a Parking Spot Node (ESP32 + HC-SR04 + MQ-2 + LEDs)
    or an Access Barrier Node (ESP32-CAM + IR + servo). The edge only needs the
    credentials to authenticate it.
    """

    def __init__(self, device_id, api_key, label=None):
        self.device_id = device_id
        self.api_key = api_key
        self.label = label
