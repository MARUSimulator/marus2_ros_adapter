#!/usr/bin/env python3

import sys
import os

# Add package directory and marus2_proto subdirectory to sys.path so generated protobufs resolve cleanly
pkg_dir = os.path.abspath(os.path.dirname(__file__))
proto_dir = os.path.join(pkg_dir, "marus2_proto")
for p in [pkg_dir, proto_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from concurrent import futures
import grpc

from .grpc_utils import ros_handle as rh

try:
    import ping_pb2_grpc
    import sensor_streaming_pb2_grpc
    import remote_control_pb2_grpc
    import tf_pb2_grpc
    import parameter_server_pb2_grpc
    import simulation_control_pb2_grpc
    import visualization_pb2_grpc
    import acoustic_transmission_pb2_grpc
except ImportError:
    from .marus2_proto import ping_pb2_grpc
    from .marus2_proto import sensor_streaming_pb2_grpc
    from .marus2_proto import remote_control_pb2_grpc
    from .marus2_proto import tf_pb2_grpc
    from .marus2_proto import parameter_server_pb2_grpc
    from .marus2_proto import simulation_control_pb2_grpc
    from .marus2_proto import visualization_pb2_grpc
    from .marus2_proto import acoustic_transmission_pb2_grpc

from .services.ping_service import PingService
from .services.sensor_streaming import SensorStreaming
from .services.remote_control import RemoteControl
from .services.parameter_server import ParameterServer
from .services.frame_service import FrameService
from .services.simulation_control import SimulationControl
from .services.visualization import Visualization
from .services.acoustic_transmission import AcousticTransmission
from .services.sensor_callbacks import (
    publish_image,
    publish_sonar_image,
    publish_imu,
    publish_pose,
    publish_depth,
    publish_dvl,
    publish_sonar,
    publish_sonar_fix,
    publish_ais,
    publish_gnss,
    publish_pointcloud,
    publish_pointcloud2,
)


def serve(server_ip: str, server_port: int):
    """
    Add service handles to server and start server execution
    """
    MAX_MESSAGE_LENGTH = 100 * 1024 * 1024
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=100),
        options=[
            ("grpc.max_send_message_length", MAX_MESSAGE_LENGTH),
            ("grpc.max_receive_message_length", MAX_MESSAGE_LENGTH),
        ],
    )

    ping_pb2_grpc.add_PingServicer_to_server(PingService(), server)

    sensor_streaming_callbacks = {
        "StreamCameraSensor": [publish_image],
        "StreamSonarImage": [publish_sonar_image],
        "StreamImuSensor": [publish_imu],
        "StreamPoseSensor": [publish_pose],
        "StreamDepthSensor": [publish_depth],
        "StreamDvlSensor": [publish_dvl],
        "StreamSonarSensor": [publish_sonar],
        "StreamSonarFixSensor": [publish_sonar_fix],
        "StreamAisSensor": [publish_ais],
        "StreamGnssSensor": [publish_gnss],
        "StreamLidarSensor": [publish_pointcloud],
        "StreamPointCloud": [publish_pointcloud],
        "StreamPointCloud2": [publish_pointcloud2],
    }

    sensor_streaming_pb2_grpc.add_SensorStreamingServicer_to_server(
        SensorStreaming(sensor_streaming_callbacks), server
    )

    remote_control_pb2_grpc.add_RemoteControlServicer_to_server(
        RemoteControl(), server
    )

    tf_pb2_grpc.add_TfServicer_to_server(FrameService(), server)

    parameter_server_pb2_grpc.add_ParameterServerServicer_to_server(
        ParameterServer(), server
    )

    simulation_control_pb2_grpc.add_SimulationControlServicer_to_server(
        SimulationControl(), server
    )

    visualization_pb2_grpc.add_VisualizationServicer_to_server(
        Visualization(), server
    )

    acoustic_transmission_pb2_grpc.add_AcousticTransmissionServicer_to_server(
        AcousticTransmission(), server
    )

    listen_addr = f"{server_ip}:{server_port}"
    server.add_insecure_port(listen_addr)
    rh.loginfo(f"gRPC ROS adapter server running on {listen_addr}")
    server.start()

    try:
        rh.spin()
    except KeyboardInterrupt:
        pass
    finally:
        rh.loginfo("Stopping gRPC server...")
        server.stop(grace=1.0)
        rh.shutdown()


def main():
    rh.init("synthetic_data")
    server_ip = str(rh.get_param("server_ip") or "0.0.0.0")
    raw_port = rh.get_param("server_port") or rh.get_param("port") or 30052
    server_port = int(raw_port)

    serve(server_ip, server_port)


if __name__ == "__main__":
    main()
