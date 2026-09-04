try:
    import simulation_control_pb2
    import simulation_control_pb2_grpc
except ImportError:
    try:
        from ..marus2_proto import simulation_control_pb2
        from ..marus2_proto import simulation_control_pb2_grpc
    except ImportError:
        from marus2_ros_adapter.marus2_proto import simulation_control_pb2
        from marus2_ros_adapter.marus2_proto import simulation_control_pb2_grpc

from ..grpc_utils import ros_handle as rh
from rosgraph_msgs.msg import Clock


class SimulationControl(simulation_control_pb2_grpc.SimulationControlServicer):
    """
    Service used to control the flow of the simulation.
    Simulator dictates the clock and issues a Step request for ROS nodes.
    """

    def __init__(self):
        self.clock_publisher = rh.Publisher(Clock, "/clock", qos_profile=10)
        self.start_time = None
        self.current_time = None

    def SetStartTime(self, request, context):
        self.start_time = rh.Time.from_sec(float(request.timeSecs))
        self.current_time = self.start_time
        sim_clock = Clock()
        sim_clock.clock = self.start_time
        self.clock_publisher.publish(sim_clock)
        return simulation_control_pb2.SetStartTimeResponse(success=True)

    def Step(self, request, context):
        self.current_time = rh.Time(secs=float(request.totalTimeSecs), nsecs=float(request.totalTimeNsecs))
        sim_clock = Clock()
        sim_clock.clock = self.current_time
        self.clock_publisher.publish(sim_clock)
        return simulation_control_pb2.StepResponse(success=True)