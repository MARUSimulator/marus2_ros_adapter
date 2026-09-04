import sys
import os
import types

# Ensure workspace and packages are in sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
pkg_dir = os.path.join(repo_root, "marus2_ros_adapter")
proto_dir = os.path.join(pkg_dir, "marus2_proto")

# Set Protobuf Python fallback for Protobuf >= 4 compatibility with legacy descriptors
if "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION" not in os.environ:
    os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

for p in [proto_dir, pkg_dir, repo_root]:
    if p not in sys.path:
        sys.path.insert(0, p)


def _create_mock_module(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


# Check if ROS 2 packages are missing; if so, create mock stubs for unit testing
if "rclpy" not in sys.modules:
    try:
        import rclpy
    except ImportError:
        rclpy = _create_mock_module("rclpy")
        rclpy.ok = lambda: True
        rclpy.init = lambda args=None: None
        rclpy.shutdown = lambda: None
        rclpy.spin = lambda node: None
        rclpy.spin_once = lambda node, timeout_sec=None: None

        class MockNode:
            def __init__(self, name="", namespace="", **kwargs):
                self.name = name
                self.namespace = namespace
                self._params = {}
                self._logger = MockLogger()

            def declare_parameter(self, name, default=None):
                self._params[name] = MockParam(name, default)
                return self._params[name]

            def has_parameter(self, name):
                return name in self._params

            def get_parameter(self, name):
                return self._params.get(name, MockParam(name, None))

            def set_parameters(self, params):
                for p in params:
                    self._params[p.name] = p

            def create_publisher(self, msg_type, topic, qos_profile):
                return MockPublisher(topic, msg_type)

            def create_subscription(self, msg_type, topic, callback, qos_profile=10):
                return MockSubscription(topic, msg_type, callback)

            def create_client(self, srv_type, srv_name):
                return MockClient(srv_name, srv_type)

            def get_logger(self):
                return self._logger

            def get_clock(self):
                return MockClock()

            def destroy_node(self):
                pass

        class MockParam:
            def __init__(self, name, value):
                self.name = name
                self.value = value

        class MockPublisher:
            def __init__(self, topic, msg_type):
                self.topic = topic
                self.msg_type = msg_type
                self.published = []

            def publish(self, msg):
                self.published.append(msg)
                # Dispatch immediately to local subscribers on same topic for testing
                sub = MockSubscription.registry.get(self.topic)
                if sub is not None:
                    sub.callback(msg)

        class MockSubscription:
            registry = {}

            def __init__(self, topic, msg_type, callback):
                self.topic = topic
                self.msg_type = msg_type
                self.callback = callback
                MockSubscription.registry[topic] = self

            def destroy(self):
                MockSubscription.registry.pop(self.topic, None)

        class MockClient:
            def __init__(self, name, srv_type):
                self.name = name
                self.srv_type = srv_type

            def wait_for_service(self, timeout_sec=1.0):
                return True

            def call_async(self, req):
                import concurrent.futures
                f = concurrent.futures.Future()
                f.set_result(object())
                return f

        class MockLogger:
            def info(self, msg): pass
            def warn(self, msg): pass
            def error(self, msg): pass
            def debug(self, msg): pass

        class MockClock:
            def now(self):
                return MockTimeObj()

        class MockTimeObj:
            def to_msg(self):
                from builtin_interfaces.msg import Time
                return Time(sec=100, nanosec=500)

        rclpy.create_node = lambda name, **kwargs: MockNode(name, **kwargs)
        rclpy.node = _create_mock_module("rclpy.node")
        rclpy.node.Node = MockNode
        rclpy.parameter = _create_mock_module("rclpy.parameter")
        rclpy.parameter.Parameter = MockParam


if "builtin_interfaces" not in sys.modules:
    try:
        import builtin_interfaces.msg
    except ImportError:
        bi = _create_mock_module("builtin_interfaces")
        bi_msg = _create_mock_module("builtin_interfaces.msg")

        class Time:
            def __init__(self, sec=0, nanosec=0):
                self.sec = int(sec)
                self.nanosec = int(nanosec)

        bi_msg.Time = Time
        bi.msg = bi_msg


if "std_msgs" not in sys.modules:
    try:
        import std_msgs.msg
    except ImportError:
        sm = _create_mock_module("std_msgs")
        sm_msg = _create_mock_module("std_msgs.msg")

        class Header:
            def __init__(self, stamp=None, frame_id=""):
                from builtin_interfaces.msg import Time
                self.stamp = stamp or Time()
                self.frame_id = frame_id

        class Float32:
            def __init__(self, data=0.0):
                self.data = float(data)

        class ColorRGBA:
            def __init__(self, r=0.0, g=0.0, b=0.0, a=0.0):
                self.r, self.g, self.b, self.a = float(r), float(g), float(b), float(a)

        class Float32MultiArray:
            def __init__(self, data=None):
                self.data = data or []

        class Int32MultiArray:
            def __init__(self, data=None):
                self.data = data or []

        sm_msg.Header = Header
        sm_msg.Float32 = Float32
        sm_msg.ColorRGBA = ColorRGBA
        sm_msg.Float32MultiArray = Float32MultiArray
        sm_msg.Int32MultiArray = Int32MultiArray
        sm.msg = sm_msg


if "geometry_msgs" not in sys.modules:
    try:
        import geometry_msgs.msg
    except ImportError:
        gm = _create_mock_module("geometry_msgs")
        gm_msg = _create_mock_module("geometry_msgs.msg")

        class Vector3:
            def __init__(self, x=0.0, y=0.0, z=0.0):
                self.x, self.y, self.z = float(x), float(y), float(z)

        class Point:
            def __init__(self, x=0.0, y=0.0, z=0.0):
                self.x, self.y, self.z = float(x), float(y), float(z)

        class Point32:
            def __init__(self, x=0.0, y=0.0, z=0.0):
                self.x, self.y, self.z = float(x), float(y), float(z)

        class Quaternion:
            def __init__(self, x=0.0, y=0.0, z=0.0, w=1.0):
                self.x, self.y, self.z, self.w = float(x), float(y), float(z), float(w)

        class Pose:
            def __init__(self, position=None, orientation=None):
                self.position = position if position is not None else Point()
                self.orientation = orientation if orientation is not None else Quaternion()

        class PoseWithCovariance:
            def __init__(self, pose=None, covariance=None):
                self.pose = pose if pose is not None else Pose()
                self.covariance = covariance if covariance is not None else [0.0] * 36

        class PoseWithCovarianceStamped:
            def __init__(self, header=None, pose=None):
                from std_msgs.msg import Header
                self.header = header or Header()
                self.pose = pose if pose is not None else PoseWithCovariance()

        class Twist:
            def __init__(self, linear=None, angular=None):
                self.linear = linear if linear is not None else Vector3()
                self.angular = angular if angular is not None else Vector3()

        class TwistWithCovariance:
            def __init__(self, twist=None, covariance=None):
                self.twist = twist if twist is not None else Twist()
                self.covariance = covariance if covariance is not None else [0.0] * 36

        class TwistWithCovarianceStamped:
            def __init__(self, header=None, twist=None):
                from std_msgs.msg import Header
                self.header = header or Header()
                self.twist = twist if twist is not None else TwistWithCovariance()

        class Transform:
            def __init__(self, translation=None, rotation=None):
                self.translation = translation if translation is not None else Vector3()
                self.rotation = rotation if rotation is not None else Quaternion()

        class TransformStamped:
            def __init__(self, header=None, child_frame_id="", transform=None):
                from std_msgs.msg import Header
                self.header = header or Header()
                self.child_frame_id = child_frame_id
                self.transform = transform if transform is not None else Transform()

        gm_msg.Vector3 = Vector3
        gm_msg.Point = Point
        gm_msg.Point32 = Point32
        gm_msg.Quaternion = Quaternion
        gm_msg.Pose = Pose
        gm_msg.PoseWithCovariance = PoseWithCovariance
        gm_msg.PoseWithCovarianceStamped = PoseWithCovarianceStamped
        gm_msg.Twist = Twist
        gm_msg.TwistWithCovariance = TwistWithCovariance
        gm_msg.TwistWithCovarianceStamped = TwistWithCovarianceStamped
        gm_msg.Transform = Transform
        gm_msg.TransformStamped = TransformStamped
        gm.msg = gm_msg


if "sensor_msgs" not in sys.modules:
    try:
        import sensor_msgs.msg
    except ImportError:
        sms = _create_mock_module("sensor_msgs")
        sms_msg = _create_mock_module("sensor_msgs.msg")

        class ChannelFloat32:
            def __init__(self, name="", values=None):
                self.name = name
                self.values = values or []

        class PointField:
            def __init__(self, name="", offset=0, datatype=0, count=0):
                self.name, self.offset, self.datatype, self.count = name, offset, datatype, count

        class PointCloud:
            def __init__(self, header=None, points=None, channels=None):
                from std_msgs.msg import Header
                self.header = header or Header()
                self.points = points or []
                self.channels = channels or []

        class PointCloud2:
            def __init__(self, header=None, height=0, width=0, fields=None, is_bigendian=False, point_step=0, row_step=0, data=b"", is_dense=False):
                from std_msgs.msg import Header
                self.header = header or Header()
                self.height, self.width = height, width
                self.fields = fields or []
                self.is_bigendian = is_bigendian
                self.point_step, self.row_step = point_step, row_step
                self.data = data
                self.is_dense = is_dense

        class Imu:
            def __init__(self, header=None):
                from std_msgs.msg import Header
                from geometry_msgs.msg import Vector3, Quaternion
                self.header = header or Header()
                self.linear_acceleration = Vector3()
                self.angular_velocity = Vector3()
                self.orientation = Quaternion()

        class NavSatStatus:
            def __init__(self, status=0, service=0):
                self.status, self.service = status, service

        class NavSatFix:
            def __init__(self, header=None, status=None, latitude=0.0, longitude=0.0, altitude=0.0):
                from std_msgs.msg import Header
                self.header = header or Header()
                self.status = status or NavSatStatus()
                self.latitude, self.longitude, self.altitude = latitude, longitude, altitude

        class Image:
            def __init__(self, header=None, height=0, width=0, encoding="", is_bigendian=0, step=0, data=b""):
                from std_msgs.msg import Header
                self.header = header or Header()
                self.height, self.width = height, width
                self.encoding, self.is_bigendian, self.step, self.data = encoding, is_bigendian, step, data

        class CompressedImage:
            def __init__(self, header=None, format="", data=b""):
                from std_msgs.msg import Header
                self.header = header or Header()
                self.format, self.data = format, data

        sms_msg.ChannelFloat32 = ChannelFloat32
        sms_msg.PointField = PointField
        sms_msg.PointCloud = PointCloud
        sms_msg.PointCloud2 = PointCloud2
        sms_msg.Imu = Imu
        sms_msg.NavSatStatus = NavSatStatus
        sms_msg.NavSatFix = NavSatFix
        sms_msg.Image = Image
        sms_msg.CompressedImage = CompressedImage
        sms.msg = sms_msg


if "visualization_msgs" not in sys.modules:
    try:
        import visualization_msgs.msg
    except ImportError:
        vm = _create_mock_module("visualization_msgs")
        vm_msg = _create_mock_module("visualization_msgs.msg")

        class Marker:
            def __init__(self):
                from std_msgs.msg import Header, ColorRGBA
                from geometry_msgs.msg import Pose, Vector3
                from builtin_interfaces.msg import Time
                self.header = Header()
                self.ns = ""
                self.id = 0
                self.type = 0
                self.action = 0
                self.pose = Pose()
                self.scale = Vector3()
                self.color = ColorRGBA()
                self.lifetime = Time()
                self.frame_locked = False
                self.points = []
                self.colors = []
                self.text = ""
                self.mesh_resource = ""
                self.mesh_use_embedded_materials = False

        class MarkerArray:
            def __init__(self, markers=None):
                self.markers = markers or []

        vm_msg.Marker = Marker
        vm_msg.MarkerArray = MarkerArray
        vm.msg = vm_msg


if "tf2_msgs" not in sys.modules:
    try:
        import tf2_msgs.msg
    except ImportError:
        tfm = _create_mock_module("tf2_msgs")
        tfm_msg = _create_mock_module("tf2_msgs.msg")

        class TFMessage:
            def __init__(self, transforms=None):
                self.transforms = transforms or []

        tfm_msg.TFMessage = TFMessage
        tfm.msg = tfm_msg


if "rosgraph_msgs" not in sys.modules:
    try:
        import rosgraph_msgs.msg
    except ImportError:
        rgm = _create_mock_module("rosgraph_msgs")
        rgm_msg = _create_mock_module("rosgraph_msgs.msg")

        class Clock:
            def __init__(self, clock=None):
                from builtin_interfaces.msg import Time
                self.clock = clock or Time()

        rgm_msg.Clock = Clock
        rgm.msg = rgm_msg


if "cv_bridge" not in sys.modules:
    try:
        import cv_bridge
    except ImportError:
        cvb = _create_mock_module("cv_bridge")

        class CvBridgeError(Exception):
            pass

        class CvBridge:
            def cv2_to_imgmsg(self, cv_img, encoding="bgr8"):
                from sensor_msgs.msg import Image
                img = Image()
                if hasattr(cv_img, "shape"):
                    img.height = cv_img.shape[0]
                    img.width = cv_img.shape[1]
                return img

            def imgmsg_to_cv2(self, img_msg, desired_encoding="passthrough"):
                import numpy as np
                return np.zeros((img_msg.height or 10, img_msg.width or 10, 3), dtype=np.uint8)

        cvb.CvBridge = CvBridge
        cvb.CvBridgeError = CvBridgeError

# Synchronize sys.modules for protobuf modules to avoid dual-loading differences
import importlib
for mod_name in ["geometry_pb2", "sensor_streaming_pb2", "sensor_pb2", "std_pb2", "labust_pb2", "marine_pb2"]:
    try:
        m = importlib.import_module(mod_name)
        sys.modules[f"marus2_ros_adapter.marus2_proto.{mod_name}"] = m
        sys.modules[f"marus2_proto.{mod_name}"] = m
        sys.modules[f"marus2_ros_adapter.protobuf.{mod_name}"] = m
        sys.modules[f"protobuf.{mod_name}"] = m
    except Exception:
        pass

