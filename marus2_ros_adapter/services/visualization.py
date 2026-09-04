try:
    import visualization_pb2
    import visualization_pb2_grpc
    import std_pb2
except ImportError:
    try:
        from ..marus2_proto import visualization_pb2
        from ..marus2_proto import visualization_pb2_grpc
        from ..marus2_proto import std_pb2
    except ImportError:
        from marus2_ros_adapter.marus2_proto import visualization_pb2
        from marus2_ros_adapter.marus2_proto import visualization_pb2_grpc
        from marus2_ros_adapter.marus2_proto import std_pb2

from ..grpc_utils import topic_streamer
from ..grpc_utils import ros_handle as rh
from ..grpc_utils import extensions  # Registers .as_msg() on Pose, Vector3, etc.
from visualization_msgs.msg import Marker, MarkerArray


class Visualization(visualization_pb2_grpc.VisualizationServicer):

    def __init__(self, callbacks=None):
        self._callbacks = callbacks or {}
        self._streamer1 = topic_streamer.Streamer(
            Visualization.make_response, Marker)
        self._streamer2 = topic_streamer.Streamer(
            Visualization.make_response, MarkerArray)

    def SetMarker(self, request, context):
        for msg in self._streamer1.start_stream(request, context):
            if not context.is_active():
                break

            response = None
            try:
                response = Visualization.Ros2Msg(msg)
            except Exception as e:
                rh.logerr(f"SetMarker conversion error: {e}")
                continue

            callbacks = self._callbacks.get("SetMarker", [])
            for c in callbacks:
                c(response, context)

            yield response

    def SetMarkerArray(self, request, context):
        for msg in self._streamer2.start_stream(request, context):
            if not context.is_active():
                break

            response = visualization_pb2.MarkerArray()
            arr = []
            for marker in msg.markers:
                try:
                    arr.append(Visualization.Ros2Msg(marker))
                except Exception as e:
                    rh.logerr(f"SetMarkerArray conversion error: {e}")
            response.markers.extend(arr)

            callbacks = self._callbacks.get("SetMarkerArray", [])
            for c in callbacks:
                c(response, context)

            yield response

    @staticmethod
    def make_response(response):
        return response

    @staticmethod
    def Ros2Msg(request):
        response = visualization_pb2.Marker()
        response.header.frameId = request.header.frame_id
        response.header.timestamp = request.header.stamp.sec + request.header.stamp.nanosec * 1e-9

        response.ns = request.ns
        response.id = request.id
        response.type = request.type
        response.action = request.action
        response.pose.CopyFrom(request.pose.as_msg())
        response.scale.CopyFrom(request.scale.as_msg())
        response.color.CopyFrom(request.color.as_msg())
        response.lifetime = getattr(request.lifetime, 'sec', getattr(request.lifetime, 'secs', 0))
        response.frameLocked = request.frame_locked
        response.points.extend([x.as_msg() for x in request.points])
        response.colors.extend([x.as_msg() for x in request.colors])
        response.text = request.text
        response.meshResource = request.mesh_resource
        response.meshUseEmbeddedMaterials = request.mesh_use_embedded_materials
        return response