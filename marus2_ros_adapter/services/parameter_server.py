try:
    import parameter_server_pb2
    import parameter_server_pb2_grpc
    from std_pb2 import Empty
except ImportError:
    try:
        from ..marus2_proto import parameter_server_pb2
        from ..marus2_proto import parameter_server_pb2_grpc
        from ..marus2_proto.std_pb2 import Empty
    except ImportError:
        from marus2_ros_adapter.marus2_proto import parameter_server_pb2
        from marus2_ros_adapter.marus2_proto import parameter_server_pb2_grpc
        from marus2_ros_adapter.marus2_proto.std_pb2 import Empty

from ..grpc_utils import ros_handle as rh


class ParameterServer(parameter_server_pb2_grpc.ParameterServerServicer):

    def __init__(self):
        pass

    def GetParameter(self, request, context):
        param = rh.get_param(request.name, None)
        response = parameter_server_pb2.ParamValue()
        # In Python bool is subclass of int, so check bool FIRST
        if isinstance(param, bool):
            response.valueBool = param
        elif isinstance(param, int):
            response.valueInt = param
        elif isinstance(param, float):
            response.valueDouble = param
        elif isinstance(param, str):
            response.valueStr = param
        elif param is None:
            pass
        else:
            raise ValueError(f"Type of parameter {type(param)} not supported")

        return response

    def SetParameter(self, request, context):
        param = request.value
        which_one = param.WhichOneof("parameterValue")
        if which_one is not None:
            value = getattr(param, which_one, None)
            if value is not None:
                rh.set_param(request.name, value)

        return Empty()
