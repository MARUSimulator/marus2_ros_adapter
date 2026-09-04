import os
import sys

ROS_1 = 1
ROS_2 = 2

ROS_VERSION = int(os.getenv("ROS_VERSION", "2"))
_HANDLER = None
_NODE = None
IS_INIT = False

if ROS_VERSION == ROS_1:
    try:
        import rospy
        _HANDLER = rospy
    except ImportError:
        _HANDLER = None
elif ROS_VERSION == ROS_2:
    try:
        import rclpy
        from rclpy.parameter import Parameter
        from builtin_interfaces.msg import Time as RosTime
        _HANDLER = rclpy
    except ImportError:
        _HANDLER = None

        class Parameter:
            def __init__(self, name, value=None):
                self.name = name
                self.value = value

        class RosTime:
            def __init__(self, sec=0, nanosec=0):
                self.sec = sec
                self.nanosec = nanosec

            def __repr__(self):
                return f"Time(sec={self.sec}, nanosec={self.nanosec})"


def init(node_name: str, namespace: str = "", args=None):
    global _NODE
    global IS_INIT
    if ROS_VERSION == ROS_1:
        if _HANDLER is not None:
            _NODE = _HANDLER.init_node(node_name, argv=args)
    elif ROS_VERSION == ROS_2:
        if _HANDLER is not None:
            if not _HANDLER.ok():
                _HANDLER.init(args=args)
            _NODE = _HANDLER.create_node(
                node_name,
                namespace=namespace,
                allow_undeclared_parameters=True,
                automatically_declare_parameters_from_overrides=True
            )
        else:
            _NODE = None
    IS_INIT = True
    return _NODE


def get_node():
    return _NODE


def spin():
    if ROS_VERSION == ROS_1 and _HANDLER is not None:
        _HANDLER.spin()
    elif ROS_VERSION == ROS_2 and _HANDLER is not None and _NODE is not None:
        _HANDLER.spin(_NODE)


def spin_once(timeout_sec=None):
    if ROS_VERSION == ROS_1 and _HANDLER is not None:
        _HANDLER.spin_once()
    elif ROS_VERSION == ROS_2 and _HANDLER is not None and _NODE is not None:
        _HANDLER.spin_once(_NODE, timeout_sec=timeout_sec)


def shutdown():
    global _NODE, IS_INIT
    if _NODE is not None:
        try:
            _NODE.destroy_node()
        except Exception:
            pass
        _NODE = None
    if ROS_VERSION == ROS_2 and _HANDLER is not None and _HANDLER.ok():
        try:
            _HANDLER.shutdown()
        except Exception:
            pass
    IS_INIT = False


def get_param(param_name: str, default=None):
    if ROS_VERSION == ROS_1 and _HANDLER is not None:
        return _HANDLER.get_param(f"{param_name}", default)
    elif ROS_VERSION == ROS_2:
        if param_name.startswith('~') or param_name.startswith('/'):
            param_name = param_name[1:]
        if _NODE is None:
            return default
        if not _NODE.has_parameter(param_name):
            _NODE.declare_parameter(param_name, default)
        param = _NODE.get_parameter(param_name)
        val = param.value
        return val if val is not None else default


def set_param(param_name: str, value):
    if ROS_VERSION == ROS_1 and _HANDLER is not None:
        _HANDLER.set_param(param_name, value)
    elif ROS_VERSION == ROS_2:
        if param_name.startswith('~') or param_name.startswith('/'):
            param_name = param_name[1:]
        if _NODE is not None:
            if not _NODE.has_parameter(param_name):
                _NODE.declare_parameter(param_name, value)
            else:
                _NODE.set_parameters([Parameter(param_name, value=value)])


class _Subscription:

    def __call__(
        self,
        msg_type,
        topic: str,
        callback,
        qos_profile=10,
        *args, **kwargs
    ):
        if ROS_VERSION == ROS_1 and _HANDLER is not None:
            return _HANDLER.Subscriber(topic, msg_type, callback, queue_size=qos_profile)
        elif ROS_VERSION == ROS_2 and _NODE is not None:
            return _NODE.create_subscription(msg_type, topic, callback, qos_profile=qos_profile)
        return None


class _Publisher:

    def __call__(
        self,
        msg_type,
        topic: str,
        qos_profile=10
    ):
        if ROS_VERSION == ROS_1 and _HANDLER is not None:
            return _HANDLER.Publisher(topic, msg_type, queue_size=qos_profile)
        elif ROS_VERSION == ROS_2 and _NODE is not None:
            return _NODE.create_publisher(msg_type, topic, qos_profile)
        return None


class _Time:

    def now(self):
        if ROS_VERSION == ROS_1 and _HANDLER is not None:
            return _HANDLER.Time.now()
        elif ROS_VERSION == ROS_2 and _NODE is not None:
            return _NODE.get_clock().now().to_msg()
        return RosTime(sec=0, nanosec=0)

    def from_sec(self, sec: float):
        if ROS_VERSION == ROS_1 and _HANDLER is not None:
            return _HANDLER.Time.from_sec(sec)
        elif ROS_VERSION == ROS_2:
            s = int(sec)
            ns = int(round((sec - s) * 1e9))
            if ns >= 1_000_000_000:
                s += 1
                ns -= 1_000_000_000
            elif ns < 0:
                s -= 1
                ns += 1_000_000_000
            return RosTime(sec=s, nanosec=ns)

    def __call__(
        self,
        *,
        secs: float,
        nsecs: float
    ):
        if ROS_VERSION == ROS_1 and _HANDLER is not None:
            return _HANDLER.Time.from_sec(secs + 1e-9 * nsecs)
        elif ROS_VERSION == ROS_2:
            s = int(secs)
            total_ns = int(round(nsecs + (secs - s) * 1e9))
            s += total_ns // 1_000_000_000
            ns = total_ns % 1_000_000_000
            return RosTime(sec=s, nanosec=ns)


def logerr(msg, *args, **kwargs):
    if ROS_VERSION == ROS_1 and _HANDLER is not None:
        _HANDLER.logerr(msg)
    elif ROS_VERSION == ROS_2:
        if _NODE is not None:
            _NODE.get_logger().error(str(msg))
        else:
            print(f"[ERROR] {msg}", file=sys.stderr)


def logwarn(msg, *args, **kwargs):
    if ROS_VERSION == ROS_1 and _HANDLER is not None:
        _HANDLER.logwarn(msg)
    elif ROS_VERSION == ROS_2:
        if _NODE is not None:
            _NODE.get_logger().warn(str(msg))
        else:
            print(f"[WARN] {msg}", file=sys.stderr)


def loginfo(msg):
    if ROS_VERSION == ROS_1 and _HANDLER is not None:
        _HANDLER.loginfo(msg)
    elif ROS_VERSION == ROS_2:
        if _NODE is not None:
            _NODE.get_logger().info(str(msg))
        else:
            print(f"[INFO] {msg}")


def logdebug(msg):
    if ROS_VERSION == ROS_1 and _HANDLER is not None:
        _HANDLER.logdebug(msg)
    elif ROS_VERSION == ROS_2:
        if _NODE is not None:
            _NODE.get_logger().debug(str(msg))
        else:
            print(f"[DEBUG] {msg}")


Subscription = _Subscription()
Publisher = _Publisher()
Time = _Time()

__all__ = [
    "Subscription",
    "Publisher",
    "Time",
    "init",
    "get_node",
    "spin",
    "spin_once",
    "shutdown",
    "get_param",
    "set_param",
    "logerr",
    "logwarn",
    "loginfo",
    "logdebug"
]
