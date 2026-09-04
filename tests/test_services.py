import pytest
import os
import sys

from marus2_ros_adapter.services.parameter_server import ParameterServer
from marus2_ros_adapter.services.visualization import Visualization
from marus2_ros_adapter.services.frame_service import FrameService
from marus2_ros_adapter.services.sensor_callbacks import publish_pointcloud, publish_dvl, publish_ais
from marus2_ros_adapter.grpc_utils.ros_publisher_registry import RosPublisherRegistry
from marus2_ros_adapter.grpc_utils import ros_handle as rh

import parameter_server_pb2
import visualization_pb2
import sensor_pb2
import marine_pb2
import geometry_pb2
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import TransformStamped, Transform, Point, Vector3, Quaternion, TwistWithCovarianceStamped
from std_msgs.msg import Header


class TestParameterServer:

    def test_bool_vs_int_parameter(self):
        ps = ParameterServer()
        rh.init("test_param_node")

        # Set bool parameter
        req = parameter_server_pb2.SetParamRequest(name="test_bool")
        req.value.valueBool = True
        ps.SetParameter(req, None)
        assert rh.get_param("test_bool") is True

        # Query parameter back
        query_req = parameter_server_pb2.GetParamRequest(name="test_bool")
        resp = ps.GetParameter(query_req, None)
        assert resp.WhichOneof("parameterValue") == "valueBool"
        assert resp.valueBool is True

        # Set int parameter
        req = parameter_server_pb2.SetParamRequest(name="test_int")
        req.value.valueInt = 42
        ps.SetParameter(req, None)
        assert rh.get_param("test_int") == 42

        query_req = parameter_server_pb2.GetParamRequest(name="test_int")
        resp = ps.GetParameter(query_req, None)
        assert resp.WhichOneof("parameterValue") == "valueInt"
        assert resp.valueInt == 42

    def test_falsy_parameters(self):
        ps = ParameterServer()
        rh.init("test_param_node")

        # Integer zero
        req = parameter_server_pb2.SetParamRequest(name="zero_int")
        req.value.valueInt = 0
        ps.SetParameter(req, None)
        assert rh.get_param("zero_int") == 0

        # Boolean False
        req = parameter_server_pb2.SetParamRequest(name="false_bool")
        req.value.valueBool = False
        ps.SetParameter(req, None)
        assert rh.get_param("false_bool") is False

        # Float 0.0
        req = parameter_server_pb2.SetParamRequest(name="zero_float")
        req.value.valueDouble = 0.0
        ps.SetParameter(req, None)
        assert rh.get_param("zero_float") == 0.0


class TestVisualization:

    def test_marker_timestamp_and_array(self):
        marker = Marker()
        marker.header.frame_id = "map"
        marker.header.stamp.sec = 1600000000
        marker.header.stamp.nanosec = 500000000
        marker.ns = "test"
        marker.id = 1

        proto_marker = Visualization.Ros2Msg(marker)
        assert proto_marker.header.frameId == "map"
        assert proto_marker.header.timestamp == pytest.approx(1600000000.5)

    def test_marker_array_extend(self):
        msg = MarkerArray()
        m1 = Marker()
        m1.id = 1
        m2 = Marker()
        m2.id = 2
        msg.markers = [m1, m2]

        proto_arr = visualization_pb2.MarkerArray()
        arr = [Visualization.Ros2Msg(m) for m in msg.markers]
        proto_arr.markers.extend(arr)
        assert len(proto_arr.markers) == 2
        assert proto_arr.markers[0].id == 1
        assert proto_arr.markers[1].id == 2


class TestFrameService:

    def test_static_tf_deduplication(self):
        fs = FrameService()

        # Send first transform
        tf1 = TransformStamped()
        tf1.header.frame_id = "world"
        tf1.child_frame_id = "base_link"
        tf1.transform.translation.x = 1.0

        from tf2_msgs.msg import TFMessage
        msg1 = TFMessage(transforms=[tf1])
        fs.static_tf_callback(msg1)
        assert len(fs.static_tfs) == 1
        assert fs.static_tfs[0].transform.translation.x == 1.0

        # Send updated transform with same frame and child_frame
        tf2 = TransformStamped()
        tf2.header.frame_id = "world"
        tf2.child_frame_id = "base_link"
        tf2.transform.translation.x = 5.0
        msg2 = TFMessage(transforms=[tf2])
        fs.static_tf_callback(msg2)

        # Ensure deduplicated: still length 1, but updated value!
        assert len(fs.static_tfs) == 1
        assert fs.static_tfs[0].transform.translation.x == 5.0


class TestSensorCallbacks:

    def test_publish_dvl_velocity(self):
        class DummyContext:
            pass

        class DummyRequest:
            class Data:
                class Header:
                    timestamp = 100.5
                    frameId = "dvl_link"
                header = Header()
                velocity = geometry_pb2.Vector3(x=1.2, y=-0.3, z=0.5)
            data = Data()
            address = "/dvl_data"

        publish_dvl(DummyRequest(), DummyContext())
        pub = RosPublisherRegistry.get_publisher("/dvl_data", TwistWithCovarianceStamped)
        assert len(pub.published) > 0
        latest = pub.published[-1]
        assert latest.twist.twist.linear.x == pytest.approx(1.2)
        assert latest.twist.twist.linear.y == pytest.approx(-0.3)
        assert latest.twist.twist.linear.z == pytest.approx(0.5)

