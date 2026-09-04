from functools import wraps, partial
import numpy as np

try:
    from std_msgs.msg import Float32, ColorRGBA
    from geometry_msgs.msg import Vector3, Quaternion, Pose, Point
except ImportError:
    # Offline fallback definitions for environments without ROS 2 installed
    class Float32:
        def __init__(self, data=0.0):
            self.data = float(data)

    class ColorRGBA:
        def __init__(self, r=0.0, g=0.0, b=0.0, a=0.0):
            self.r = float(r)
            self.g = float(g)
            self.b = float(b)
            self.a = float(a)

    class Vector3:
        def __init__(self, x=0.0, y=0.0, z=0.0):
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)

    class Quaternion:
        def __init__(self, x=0.0, y=0.0, z=0.0, w=1.0):
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)
            self.w = float(w)

    class Point:
        def __init__(self, x=0.0, y=0.0, z=0.0):
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)

    class Pose:
        def __init__(self, position=None, orientation=None):
            self.position = position if position is not None else Point()
            self.orientation = orientation if orientation is not None else Quaternion()

try:
    import std_pb2 as std
    import geometry_pb2 as geometry
except ImportError:
    try:
        from ..marus2_proto import std_pb2 as std
        from ..marus2_proto import geometry_pb2 as geometry
    except ImportError:
        from marus2_ros_adapter.marus2_proto import std_pb2 as std
        from marus2_ros_adapter.marus2_proto import geometry_pb2 as geometry


def add_method(cls, name=""):
    def decorator(func, name=""):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            return func(self, *args, **kwargs)
        name = name or func.__name__
        setattr(cls, name, wrapper)
        return func
    return partial(decorator, name=name)


@add_method(Vector3, "as_msg")
def vector_as_msg(self):
    ret = geometry.Vector3()
    ret.x = float(self.x)
    ret.y = float(self.y)
    ret.z = float(self.z)
    return ret


@add_method(geometry.Vector3, "as_ros")
def vector_as_ros(self):
    vec = Vector3()
    vec.x = float(self.x)
    vec.y = float(self.y)
    vec.z = float(self.z)
    return vec


@add_method(Quaternion, "as_msg")
def quaternion_as_msg(self):
    ret = geometry.Quaternion()
    ret.x = float(self.x)
    ret.y = float(self.y)
    ret.z = float(self.z)
    ret.w = float(self.w)
    return ret


@add_method(geometry.Quaternion, "as_ros")
def quaternion_as_ros(self):
    ret = Quaternion()
    ret.x = float(self.x)
    ret.y = float(self.y)
    ret.z = float(self.z)
    ret.w = float(self.w)
    return ret


@add_method(geometry.Point, "as_ros")
def point_as_ros(self):
    ret = Point()
    ret.x = float(self.x)
    ret.y = float(self.y)
    ret.z = float(self.z)
    return ret


@add_method(Point, "as_msg")
def point_as_msg(self):
    ret = geometry.Point()
    ret.x = float(self.x)
    ret.y = float(self.y)
    ret.z = float(self.z)
    return ret


@add_method(geometry.Pose, "as_ros")
def pose_as_ros(self):
    ret = Pose()
    ret.position = self.position.as_ros()
    ret.orientation = self.orientation.as_ros()
    return ret


@add_method(Pose, "as_msg")
def pose_as_msg(self):
    ret = geometry.Pose()
    ret.position.CopyFrom(self.position.as_msg())
    ret.orientation.CopyFrom(self.orientation.as_msg())
    return ret


@add_method(ColorRGBA, "as_msg")
def color_as_msg(self):
    ret = std.ColorRGBA()
    ret.r = float(self.r)
    ret.g = float(self.g)
    ret.b = float(self.b)
    ret.a = float(self.a)
    return ret


def as_msg(ros_msg):
    if isinstance(ros_msg, Vector3):
        return vector_as_msg(ros_msg)
    if isinstance(ros_msg, Quaternion):
        return quaternion_as_msg(ros_msg)
    if isinstance(ros_msg, Point):
        return point_as_msg(ros_msg)
    if isinstance(ros_msg, Pose):
        return pose_as_msg(ros_msg)
    if isinstance(ros_msg, ColorRGBA):
        return color_as_msg(ros_msg)


def as_ros(proto_msg):
    cla = proto_msg.__class__
    if cla == geometry.Vector3:
        return vector_as_ros(proto_msg)
    if isinstance(proto_msg, geometry.Quaternion):
        return quaternion_as_ros(proto_msg)
    if isinstance(proto_msg, geometry.Point):
        return point_as_ros(proto_msg)
    if isinstance(proto_msg, geometry.Pose):
        return pose_as_ros(proto_msg)