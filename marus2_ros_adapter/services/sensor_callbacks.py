import inspect
import sys
import numpy as np
import cv2

from ..grpc_utils import ros_handle as rh
from ..grpc_utils.extensions import *
from ..grpc_utils.ros_publisher_registry import RosPublisherRegistry

from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import (
    Image,
    CompressedImage,
    Imu,
    NavSatFix,
    PointCloud,
    PointCloud2,
    PointField,
    ChannelFloat32,
)
from std_msgs.msg import Header
from geometry_msgs.msg import (
    PoseWithCovarianceStamped,
    Point,
    Point32,
    TwistWithCovarianceStamped,
)


def publish_image(request, context):
    if not hasattr(context, "bridge"):
        context.bridge = CvBridge()

    if len(request.image.data) > 0:
        img_bytes = request.image.data
        cv_image = np.frombuffer(img_bytes, dtype=np.uint8)

        # Height is specified as parameter before width
        cv_image = cv_image.reshape(request.image.height, request.image.width, 3)
        cv_image = cv2.flip(cv_image, 0)
        bgr_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)

        msg = Image()
        header = Header()
        try:
            msg = context.bridge.cv2_to_imgmsg(bgr_image, "bgr8")
            header.stamp = rh.Time.from_sec(request.image.header.timestamp)
            header.frame_id = request.image.header.frameId
            msg.header = header
        except CvBridgeError as e:
            rh.logerr(f"CvBridgeError: {e}")

        pub = RosPublisherRegistry.get_publisher(request.address.lower(), Image)
        pub.publish(msg)

    elif len(request.compressedImage.data) > 0:
        msg = CompressedImage()
        header = Header()
        header.stamp = rh.Time.from_sec(request.compressedImage.header.timestamp)
        header.frame_id = request.compressedImage.header.frameId
        msg.header = header
        msg.data = bytes(request.compressedImage.data)
        msg.format = request.compressedImage.format

        pub = RosPublisherRegistry.get_publisher(request.address.lower() + "/compressed", CompressedImage)
        pub.publish(msg)


def publish_sonar_image(request, context):
    if not hasattr(context, "bridge"):
        context.bridge = CvBridge()

    header = Header()
    header.stamp = rh.Time.from_sec(request.data.header.timestamp)
    header.frame_id = request.data.header.frameId

    img = cv2.imdecode(np.frombuffer(request.data.data, dtype=np.uint8), cv2.IMREAD_ANYCOLOR)
    msg = context.bridge.cv2_to_imgmsg(img, "bgr8")
    msg.header = header
    pub = RosPublisherRegistry.get_publisher(request.address.lower(), Image)
    pub.publish(msg)


def publish_imu(request, context):
    imu = Imu()
    imu.header.stamp = rh.Time.from_sec(request.data.header.timestamp)
    imu.header.frame_id = request.data.header.frameId
    imu.linear_acceleration = request.data.linearAcceleration.as_ros()
    imu.angular_velocity = request.data.angularVelocity.as_ros()
    imu.orientation = request.data.orientation.as_ros()

    pub = RosPublisherRegistry.get_publisher(request.address.lower(), Imu)
    pub.publish(imu)


def publish_pose(request, context):
    nav = PoseWithCovarianceStamped()
    pos = request.data.pose.pose.position
    o = request.data.pose.pose.orientation
    nav.header.stamp = rh.Time.from_sec(request.data.header.timestamp)
    nav.header.frame_id = request.data.header.frameId
    nav.pose.pose.position.x = float(pos.x)
    nav.pose.pose.position.y = float(pos.y)
    nav.pose.pose.position.z = float(pos.z)

    nav.pose.pose.orientation.w = float(o.w)
    nav.pose.pose.orientation.x = float(o.x)
    nav.pose.pose.orientation.y = float(o.y)
    nav.pose.pose.orientation.z = float(o.z)

    pub = RosPublisherRegistry.get_publisher(request.address.lower(), PoseWithCovarianceStamped)
    pub.publish(nav)


def publish_depth(request, context):
    pose = PoseWithCovarianceStamped()
    pose.header.stamp = rh.Time.from_sec(request.data.header.timestamp)
    pose.header.frame_id = request.data.header.frameId
    pose.pose.pose.position = Point(x=0.0, y=0.0, z=-float(request.data.pose.pose.position.z))

    pub = RosPublisherRegistry.get_publisher(request.address.lower(), PoseWithCovarianceStamped)
    pub.publish(pose)


def publish_dvl(request, context):
    dvl = TwistWithCovarianceStamped()
    dvl.header.stamp = rh.Time.from_sec(request.data.header.timestamp)
    dvl.header.frame_id = request.data.header.frameId

    if hasattr(request.data, "velocity"):
        dvl.twist.twist.linear.x = float(request.data.velocity.x)
        dvl.twist.twist.linear.y = float(request.data.velocity.y)
        dvl.twist.twist.linear.z = float(request.data.velocity.z)
    elif hasattr(request.data, "twist"):
        dvl.twist.twist.linear = request.data.twist.twist.linear.as_ros()

    pub = RosPublisherRegistry.get_publisher(request.address.lower(), TwistWithCovarianceStamped)
    pub.publish(dvl)


def publish_sonar_fix(request, context):
    try:
        from underwater_msgs.msg import SonarFix
    except ImportError:
        rh.logwarn("underwater_msgs.msg.SonarFix is not installed; skipping publish_sonar_fix")
        return

    sonar = SonarFix()
    sonar.bearing = float(request.bearing)
    sonar.range = float(request.range)
    pub = RosPublisherRegistry.get_publisher(request.address.lower(), SonarFix)
    pub.publish(sonar)


def publish_sonar(request, context):
    pointcloud_msg = PointCloud()
    header = Header()
    header.frame_id = request.data.header.frameId
    header.stamp = rh.Time.from_sec(request.data.header.timestamp)
    pointcloud_msg.header = header

    pointcloud_msg.points = [
        Point32(x=float(p.x), y=float(p.y), z=float(p.z))
        for p in request.data.points
    ]
    pointcloud_msg.channels = [
        ChannelFloat32(name=str(c.name), values=[float(v) for v in c.values])
        for c in request.data.channels
    ]

    pub = RosPublisherRegistry.get_publisher(request.address.lower(), PointCloud)
    pub.publish(pointcloud_msg)


def publish_gnss(request, context):
    geo_point = NavSatFix()
    geo_point.header.stamp = rh.Time.from_sec(request.data.header.timestamp)
    geo_point.header.frame_id = request.data.header.frameId
    geo_point.status.status = int(request.data.status.status)
    geo_point.status.service = int(request.data.status.service)
    geo_point.latitude = float(request.data.latitude)
    geo_point.longitude = float(request.data.longitude)
    geo_point.altitude = float(request.data.altitude)

    pub = RosPublisherRegistry.get_publisher(request.address.lower(), NavSatFix)
    pub.publish(geo_point)


def publish_ais(request, context):
    try:
        from uuv_sensor_msgs.msg import AISPositionReport
    except ImportError:
        rh.logwarn("uuv_sensor_msgs.msg.AISPositionReport is not installed; skipping publish_ais")
        return

    report = AISPositionReport()
    if hasattr(report, "header"):
        report.header.stamp = rh.Time.now()

    report.type = int(request.aisPositionReport.type)
    report.mmsi = int(request.aisPositionReport.mmsi)
    report.heading = float(request.aisPositionReport.heading)

    point = NavSatFix()
    point.latitude = float(request.aisPositionReport.geopoint.latitude)
    point.longitude = float(request.aisPositionReport.geopoint.longitude)
    point.altitude = float(request.aisPositionReport.geopoint.altitude)
    report.position = point

    sog = float(request.aisPositionReport.speedOverGround)
    cog = float(request.aisPositionReport.courseOverGround)

    if hasattr(report, "speed_over_ground"):
        report.speed_over_ground = sog
    elif hasattr(report, "speedOverGround"):
        report.speedOverGround = sog

    if hasattr(report, "course_over_ground"):
        report.course_over_ground = cog
    elif hasattr(report, "courseOverGround"):
        report.courseOverGround = cog

    pub = RosPublisherRegistry.get_publisher(request.address.lower(), AISPositionReport)
    pub.publish(report)


def publish_pointcloud(request, context):
    pointcloud_msg = PointCloud()
    header = Header()
    header.frame_id = request.data.header.frameId
    header.stamp = rh.Time.from_sec(request.data.header.timestamp)
    pointcloud_msg.header = header

    pointcloud_msg.points = [
        Point32(x=float(p.x), y=float(p.y), z=float(p.z))
        for p in request.data.points
    ]
    pointcloud_msg.channels = [
        ChannelFloat32(name=str(c.name), values=[float(v) for v in c.values])
        for c in request.data.channels
    ]

    pub = RosPublisherRegistry.get_publisher(request.address.lower(), PointCloud)
    pub.publish(pointcloud_msg)


def publish_pointcloud2(request, context):
    pointcloud_msg = PointCloud2()
    header = Header()
    header.frame_id = request.data.header.frameId
    header.stamp = rh.Time.from_sec(request.data.header.timestamp)
    pointcloud_msg.header = header

    pointcloud_msg.data = bytes(request.data.data)

    fields = []
    for f in request.data.fields:
        pf = PointField()
        pf.count = int(f.count)
        pf.datatype = int(f.datatype)
        pf.offset = int(f.offset)
        pf.name = str(f.name)
        fields.append(pf)

    pointcloud_msg.fields = fields
    pointcloud_msg.height = int(request.data.height)
    pointcloud_msg.width = int(request.data.width)
    pointcloud_msg.is_bigendian = bool(request.data.isBigEndian)
    pointcloud_msg.point_step = int(request.data.pointStep)
    pointcloud_msg.row_step = int(request.data.rowStep)
    pointcloud_msg.is_dense = bool(request.data.is_dense)

    pub = RosPublisherRegistry.get_publisher(request.address.lower(), PointCloud2)
    pub.publish(pointcloud_msg)


__all__ = [x[0] for x in inspect.getmembers(sys.modules[__name__], inspect.isfunction)]
