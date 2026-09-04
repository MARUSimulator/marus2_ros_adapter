import sys
import os
import pytest
from concurrent import futures
import grpc

try:
    import rclpy
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from marus2_ros_adapter.grpc_utils import ros_handle as rh
    from marus2_ros_adapter.services.sensor_streaming import SensorStreaming
    from marus2_ros_adapter.services.sensor_callbacks import publish_depth
    import sensor_streaming_pb2_grpc
    from sensor_streaming_pb2 import DepthStreamingRequest
    import geometry_pb2 as geometry_proto
    import std_pb2
    from tests.node_test_helper import NodeTestHelper
    HAS_DEPS = True
except ImportError as e:
    HAS_DEPS = False

TEST_PORT = 30058


@pytest.fixture(scope="module")
def ros_node():
    if not HAS_DEPS:
        pytest.skip("Dependencies not installed")
    rh.init("test_grpc_server_node")
    helper = NodeTestHelper("test_listener_node")
    yield helper
    helper.dispose()
    rh.shutdown()


@pytest.fixture(scope="module")
def grpc_server():
    if not HAS_DEPS:
        pytest.skip("Dependencies not installed")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    callbacks = {
        "StreamDepthSensor": [publish_depth]
    }
    servicer = SensorStreaming(callbacks)
    sensor_streaming_pb2_grpc.add_SensorStreamingServicer_to_server(servicer, server)
    server.add_insecure_port(f"127.0.0.1:{TEST_PORT}")
    server.start()
    yield server
    server.stop(grace=0.5)


@pytest.fixture(scope="module")
def streaming_client(grpc_server):
    channel = grpc.insecure_channel(f"127.0.0.1:{TEST_PORT}")
    client = sensor_streaming_pb2_grpc.SensorStreamingStub(channel)
    yield client
    channel.close()


class TestServer:

    def test_depth_streaming(self, streaming_client, ros_node):
        sub_name = "/depth_test"
        ros_node.subscribe(sub_name, PoseWithCovarianceStamped)

        pose = geometry_proto.PoseWithCovarianceStamped(
            pose=geometry_proto.PoseWithCovariance(
                pose=geometry_proto.Pose(
                    position=geometry_proto.Point(x=1.0, z=-2.0)
                )
            )
        )
        request = DepthStreamingRequest(data=pose, address=sub_name)

        response = streaming_client.StreamDepthSensor(iter([request]))
        assert response is not None

        has_data = ros_node.wait_for_response(sub_name, timeout=3.0)
        assert has_data is True, "Subscriber did not receive depth message within timeout"

        data = ros_node.get_subscriber_data(sub_name)
        assert data is not None
        assert data.pose.pose.position.z == 2.0, "z should be inverted to 2.0"
        assert data.pose.pose.position.x == 0.0, "x should be 0.0"
