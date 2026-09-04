import os
import sys

# Ensure Protobuf >= 4.21 (Python 3.11/3.12 / Ubuntu 24.04 / ROS 2 Jazzy)
# can load descriptors generated with protoc 3.x without TypeError
if "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION" not in os.environ:
    os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Ensure marus2_proto directory is on sys.path for flat proto imports
proto_dir = os.path.join(os.path.dirname(__file__), "marus2_proto")
if proto_dir not in sys.path:
    sys.path.insert(0, proto_dir)


