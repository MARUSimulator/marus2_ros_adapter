from ..grpc_utils import ros_handle as rh
from ..grpc_utils import topic_streamer
from ..grpc_utils.ros_publisher_registry import RosPublisherRegistry

from std_msgs.msg import Header

try:
    from uuv_sensor_msgs.msg import AcousticModemRange, AcousticModemPayload, AcousticModemRequest
except ImportError:
    AcousticModemRange = None
    AcousticModemPayload = None
    AcousticModemRequest = None

try:
    import labust_pb2
    import acoustic_transmission_pb2
    import acoustic_transmission_pb2_grpc
    import std_pb2
except ImportError:
    try:
        from ..marus2_proto import labust_pb2
        from ..marus2_proto import acoustic_transmission_pb2
        from ..marus2_proto import acoustic_transmission_pb2_grpc
        from ..marus2_proto import std_pb2
    except ImportError:
        from marus2_ros_adapter.marus2_proto import labust_pb2
        from marus2_ros_adapter.marus2_proto import acoustic_transmission_pb2
        from marus2_ros_adapter.marus2_proto import acoustic_transmission_pb2_grpc
        from marus2_ros_adapter.marus2_proto import std_pb2


class AcousticTransmission(acoustic_transmission_pb2_grpc.AcousticTransmissionServicer):
    """
    Server streaming service for acoustic modem communication.
    """

    def __init__(self, callbacks=None):
        self._callbacks = callbacks or {}
        req_type = AcousticModemRequest if AcousticModemRequest is not None else object
        self._streamer = topic_streamer.Streamer(
            AcousticTransmission.make_response, req_type
        )

    def StreamAcousticRequests(self, request, context):
        for msg in self._streamer.start_stream(request, context):
            yield msg

    def ReturnAcousticPayload(self, request, context):
        if AcousticModemRange is None or AcousticModemPayload is None:
            rh.logwarn("uuv_sensor_msgs is not installed; skipping ReturnAcousticPayload")
            return std_pb2.Empty()

        msgType = None
        msg = None
        pub_address = request.address.lower()

        if request.HasField("range") or (hasattr(request.range, "range") and request.range.range > 0):
            msgType = AcousticModemRange
            msg = AcousticModemRange()
            msg.range = float(request.range.range)
            if hasattr(msg, "range_m"):
                msg.range_m = float(request.range.rangeM)
            msg.id = int(request.range.id)

            header = Header()
            header.frame_id = request.range.header.frameId
            header.stamp = rh.Time.from_sec(request.range.header.timestamp)
            msg.header = header

        elif request.HasField("payload") or (hasattr(request.payload, "msg") and len(request.payload.msg) > 0):
            msgType = AcousticModemPayload
            msg = AcousticModemPayload()
            msg.msg_type = int(request.payload.msgType)
            msg.msg = bytes(request.payload.msg)
            msg.sender_id = int(request.payload.senderId)

            header = Header()
            header.frame_id = request.payload.header.frameId
            header.stamp = rh.Time.from_sec(request.payload.header.timestamp)
            msg.header = header

        if msgType is not None and msg is not None:
            pub = RosPublisherRegistry.get_publisher(pub_address, msgType)
            pub.publish(msg)

        callbacks = self._callbacks.get("ReturnAcousticPayload", [])
        for c in callbacks:
            c(request, context)

        return std_pb2.Empty()

    @staticmethod
    def make_response(nanomodem_req):
        request = labust_pb2.AcousticModemRequest()
        request.reqType = max(0, getattr(nanomodem_req, "req_type", 1) - 1)
        request.scheduled = bool(getattr(nanomodem_req, "scheduled", False))
        request.msg = bytes(getattr(nanomodem_req, "msg", b""))
        request.id = int(getattr(nanomodem_req, "id", 0))
        return acoustic_transmission_pb2.AcousticRequest(success=True, request=request)
