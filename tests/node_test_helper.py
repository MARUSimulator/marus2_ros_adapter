#!/usr/bin/env python3

import time

try:
    import rclpy
    from rclpy.node import Node
except ImportError:
    rclpy = None
    Node = object


class NodeTestHelper:
    """
    ROS 2 Node Test Helper for subscribing to topics and awaiting messages.
    """

    def __init__(self, node_name="test_helper_node"):
        self.node = None
        self._received_data = {}
        self._subscriptions = []

        if rclpy is not None:
            if not rclpy.ok():
                rclpy.init()
            self.node = rclpy.create_node(node_name)

    def subscribe(self, topic: str, msg_type):
        if not topic.startswith("/"):
            topic = "/" + topic

        def cb(msg):
            self._received_data[topic] = msg

        if self.node is not None:
            sub = self.node.create_subscription(msg_type, topic, cb, 10)
            self._subscriptions.append(sub)
            return sub
        return None

    def wait_for_response(self, topic: str, timeout: float = 3.0, step: float = 0.05) -> bool:
        if not topic.startswith("/"):
            topic = "/" + topic

        start = time.time()
        while (time.time() - start) < timeout:
            if self.node is not None and rclpy is not None and rclpy.ok():
                rclpy.spin_once(self.node, timeout_sec=step)
            else:
                time.sleep(step)

            if topic in self._received_data:
                return True
        return False

    def get_subscriber_data(self, topic: str):
        if not topic.startswith("/"):
            topic = "/" + topic
        return self._received_data.get(topic, None)

    def dispose(self):
        if self.node is not None:
            for sub in self._subscriptions:
                try:
                    self.node.destroy_subscription(sub)
                except Exception:
                    pass
            self._subscriptions.clear()
            try:
                self.node.destroy_node()
            except Exception:
                pass
            self.node = None

    def __del__(self):
        self.dispose()
