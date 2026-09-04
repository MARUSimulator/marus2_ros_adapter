from std_msgs.msg import Float32MultiArray

try:
    import remote_control_pb2
    import remote_control_pb2_grpc
    import std_pb2
except ImportError:
    try:
        from ..marus2_proto import remote_control_pb2
        from ..marus2_proto import remote_control_pb2_grpc
        from ..marus2_proto import std_pb2
    except ImportError:
        from marus2_ros_adapter.marus2_proto import remote_control_pb2
        from marus2_ros_adapter.marus2_proto import remote_control_pb2_grpc
        from marus2_ros_adapter.marus2_proto import std_pb2

from ..grpc_utils import topic_streamer


class RemoteControl(remote_control_pb2_grpc.RemoteControlServicer):
    """
    Server streaming service for remote control signals.
    """

    def __init__(self, callbacks=None):
        self._callbacks = callbacks or {}
        self._streamer = topic_streamer.Streamer(
            RemoteControl.make_response, Float32MultiArray
        )

    def ApplyForce(self, request, context):
        for response in self._streamer.start_stream(request, context):
            callbacks = self._callbacks.get("ApplyForce", [])
            for c in callbacks:
                c(response, context)

            yield response

    @staticmethod
    def make_response(pwm_out):
        pwm_arr = std_pb2.Float32Array()
        pwm_arr.data.extend([float(x) for x in pwm_out.data])
        return remote_control_pb2.ForceResponse(success=True, pwm=pwm_arr)