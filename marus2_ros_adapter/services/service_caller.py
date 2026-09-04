from std_msgs.msg import Int32MultiArray

try:
    import commander_service_pb2
    import commander_service_pb2_grpc
except ImportError:
    try:
        from ..marus2_proto import commander_service_pb2
        from ..marus2_proto import commander_service_pb2_grpc
    except ImportError:
        from marus2_ros_adapter.marus2_proto import commander_service_pb2
        from marus2_ros_adapter.marus2_proto import commander_service_pb2_grpc

from ..grpc_utils import ros_handle as rh
from ..grpc_utils.extensions import *


class ServiceCaller(commander_service_pb2_grpc.CommanderServicer):
    """
    Experimental service caller for pointer primitives.
    """

    def __init__(self):
        self.velcon_selection = rh.Publisher(Int32MultiArray, "/d2/velocity_selection", qos_profile=1)

    def PrimitivePointer(self, request, context):
        try:
            from labust_msgs.srv import PointerPrimitiveService
        except ImportError:
            rh.logerr("labust_msgs.srv.PointerPrimitiveService not found")
            return commander_service_pb2.PrimitivePointerResponse(success=False)

        node = rh.get_node()
        if node is None:
            rh.logerr("ROS 2 node not initialized")
            return commander_service_pb2.PrimitivePointerResponse(success=False)

        srv_name = "/d2/commander/primitive/pointer"
        client = node.create_client(PointerPrimitiveService, srv_name)
        if not client.wait_for_service(timeout_sec=1.0):
            rh.logerr(f"Service '{srv_name}' not available")
            return commander_service_pb2.PrimitivePointerResponse(success=False)

        req = PointerPrimitiveService.Request()
        req.radius = float(request.radius)
        req.radius_topic = str(request.radiusTopic)
        req.guidance_topic = str(request.guidanceTopic)
        req.fov_guidance = bool(request.fovGuidance)
        req.guidance_enable = bool(request.guidanceEnable)
        req.guidance_target = request.guidanceTarget.as_ros()
        req.vertical_offset = float(request.verticalOffset)

        future = client.call_async(req)
        # Note: in gRPC executor thread, waiting on future with short timeout:
        import time
        start_time = time.time()
        while not future.done() and (time.time() - start_time) < 2.0:
            time.sleep(0.01)

        if not future.done():
            rh.logerr(f"Service call to '{srv_name}' timed out")
            return commander_service_pb2.PrimitivePointerResponse(success=False)

        try:
            resp = future.result()
            outselect = Int32MultiArray()
            outselect.data = [2, 2, 2, 2, 2, 2]
            self.velcon_selection.publish(outselect)
            return commander_service_pb2.PrimitivePointerResponse(success=True)
        except Exception as e:
            rh.logerr(f"Service call failed: {e}")
            return commander_service_pb2.PrimitivePointerResponse(success=False)
