try:
    import sensor_streaming_pb2
    import sensor_streaming_pb2_grpc
    import sensor_pb2
    import std_pb2
except ImportError:
    try:
        from ..marus2_proto import sensor_streaming_pb2
        from ..marus2_proto import sensor_streaming_pb2_grpc
        from ..marus2_proto import sensor_pb2
        from ..marus2_proto import std_pb2
    except ImportError:
        from marus2_ros_adapter.marus2_proto import sensor_streaming_pb2
        from marus2_ros_adapter.marus2_proto import sensor_streaming_pb2_grpc
        from marus2_ros_adapter.marus2_proto import sensor_pb2
        from marus2_ros_adapter.marus2_proto import std_pb2

from ..grpc_utils import topic_streamer


class Context:
    pass


class SensorStreaming(sensor_streaming_pb2_grpc.SensorStreamingServicer):

    def __init__(self, callbacks=None):
        self.publishers = {}
        self._callbacks = callbacks or {}
        self._callback_contexts = {}

    def _get_callback_context(self, callback):
        context = self._callback_contexts.get(callback, None)
        if not context:
            context = Context()
            self._callback_contexts[callback] = context
        return context

    def trigger_callbacks(self, service_function, request):
        callbacks = self._callbacks.get(service_function.__name__, [])
        for c in callbacks:
            context = self._get_callback_context(c)
            c(request, context)

    def StreamCameraSensor(self, request_iterator, context):
        for request in request_iterator:
            self.trigger_callbacks(self.StreamCameraSensor, request)
        return std_pb2.Empty()

    def StreamLidarSensor(self, request_iterator, context):
        for request in request_iterator:
            self.trigger_callbacks(self.StreamLidarSensor, request)
        return std_pb2.Empty()

    def StreamSonarImage(self, request_iterator, context):
        for request in request_iterator:
            self.trigger_callbacks(self.StreamSonarImage, request)
        return std_pb2.Empty()

    def StreamImuSensor(self, request_iterator, context):
        for request in request_iterator:
            self.trigger_callbacks(self.StreamImuSensor, request)
        return std_pb2.Empty()

    def StreamPoseSensor(self, request_iterator, context):
        for request in request_iterator:
            self.trigger_callbacks(self.StreamPoseSensor, request)
        return std_pb2.Empty()

    def StreamDepthSensor(self, request_iterator, context):
        for request in request_iterator:
            self.trigger_callbacks(self.StreamDepthSensor, request)
        return std_pb2.Empty()

    def StreamDvlSensor(self, request_iterator, context):
        for request in request_iterator:
            self.trigger_callbacks(self.StreamDvlSensor, request)
        return std_pb2.Empty()

    def StreamSonarSensor(self, request_iterator, context):
        for request in request_iterator:
            self.trigger_callbacks(self.StreamSonarSensor, request)
        return std_pb2.Empty()

    def StreamGnssSensor(self, request_iterator, context):
        for request in request_iterator:
            self.trigger_callbacks(self.StreamGnssSensor, request)
        return std_pb2.Empty()

    def StreamAisSensor(self, request_iterator, context):
        for request in request_iterator:
            self.trigger_callbacks(self.StreamAisSensor, request)
        return std_pb2.Empty()

    def StreamPointCloud(self, request_iterator, context):
        for request in request_iterator:
            self.trigger_callbacks(self.StreamPointCloud, request)
        return std_pb2.Empty()

    def StreamPointCloud2(self, request_iterator, context):
        for request in request_iterator:
            self.trigger_callbacks(self.StreamPointCloud2, request)
        return std_pb2.Empty()

    def RequestPointCloud2(self, request, context):
        from sensor_msgs.msg import PointCloud2 as PC2
        _streamer = topic_streamer.Streamer(lambda x: x, PC2)
        for msg in _streamer.start_stream(request, context):
            if not context.is_active():
                break

            response = sensor_streaming_pb2.PointCloud2StreamingRequest()
            response.data.height = msg.height
            response.data.width = msg.width
            response.data.isBigEndian = msg.is_bigendian
            response.data.pointStep = msg.point_step
            response.data.rowStep = msg.row_step
            response.data.is_dense = msg.is_dense

            if hasattr(msg.header.stamp, "to_sec"):
                response.data.header.timestamp = msg.header.stamp.to_sec()
            else:
                response.data.header.timestamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

            response.data.header.frameId = msg.header.frame_id
            response.data.data = bytes(msg.data)

            fields = []
            for pf in msg.fields:
                field = sensor_pb2.PointField()
                field.name = pf.name
                field.offset = pf.offset
                field.datatype = pf.datatype
                field.count = pf.count
                fields.append(field)
            response.data.fields.extend(fields)

            callbacks = self._callbacks.get("RequestPointCloud2", [])
            for c in callbacks:
                c(response, context)
            yield response
