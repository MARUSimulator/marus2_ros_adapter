try:
    import ping_pb2
    import ping_pb2_grpc
except ImportError:
    try:
        from ..marus2_proto import ping_pb2
        from ..marus2_proto import ping_pb2_grpc
    except ImportError:
        from marus2_ros_adapter.marus2_proto import ping_pb2
        from marus2_ros_adapter.marus2_proto import ping_pb2_grpc


class PingService(ping_pb2_grpc.PingServicer):
    """
    Service used to send and receive dummy data to verify connectivity.
    """

    def __init__(self):
        pass

    def Ping(self, request, context):
        request.value = 1
        return request