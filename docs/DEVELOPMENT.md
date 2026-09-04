# Developer Guide

Welcome to the `marus2_ros_adapter` developer guide! This document provides instructions for extending the adapter, adding new sensors or services, compiling protobuf definitions, and maintaining cross-distribution compatibility across ROS 2.

---

## 1. Codebase Organization

The repository follows a clean, modular structure separating ROS 2 bindings, gRPC servicers, serialization utilities, and launch configurations:

```
marus2_ros_adapter/
├── config/
│   └── server.yaml                   # Default server parameters (IP, port)
├── docs/
│   ├── ARCHITECTURE.md               # Threading model, dataflow, coordinate frames
│   ├── SERVICES.md                   # Full reference of all gRPC services & ROS topics
│   └── DEVELOPMENT.md                # This guide
├── launch/
│   └── ros2_server_launch.py         # ROS 2 Python launch description
├── marus2_ros_adapter/
│   ├── __init__.py                   # Package init & Protobuf python runtime fallback
│   ├── server.py                     # Main node entry point & gRPC server lifecycle
│   ├── grpc_utils/                   # Thread-safe ROS 2 & gRPC bridging utilities
│   │   ├── extensions.py             # Vector/Point/Quaternion conversion helpers
│   │   ├── ros_handle.py             # ROS 2 rclpy node wrapper (singleton)
│   │   ├── ros_publisher_registry.py # Thread-safe publisher registry with locks
│   │   └── topic_streamer.py         # Queue-backed thread-safe ROS-to-gRPC streamer
│   ├── marus2_proto/                 # Compiled gRPC stubs from marus2-proto submodule
│   │   ├── std_pb2.py / std_pb2_grpc.py
│   │   ├── sensor_streaming_pb2.py / sensor_streaming_pb2_grpc.py
│   │   ├── tf_pb2.py / tf_pb2_grpc.py
│   │   ├── remote_control_pb2.py / remote_control_pb2_grpc.py
│   │   ├── simulation_control_pb2.py / simulation_control_pb2_grpc.py
│   │   ├── param_server_pb2.py / param_server_pb2_grpc.py
│   │   └── ...
│   └── services/                     # gRPC Servicer implementations
│       ├── acoustic_transmission.py  # Underwater acoustic modem simulation
│       ├── frame_service.py          # TF and static TF synchronization
│       ├── parameter_server.py       # Parameter querying and modification
│       ├── remote_control.py         # Thruster force & motor commands
│       ├── sensor_callbacks.py       # Raw data conversion & ROS topic publishing
│       ├── sensor_streaming.py       # Client-streaming RPC endpoints for sensors
│       ├── service_caller.py         # ROS 2 service proxy
│       ├── simulation_control.py     # Stepping & /clock publisher
│       └── visualization.py          # Marker and MarkerArray streamer
├── resource/
│   └── marus2_ros_adapter            # Colcon index resource marker
├── tests/
│   ├── conftest.py                   # Offline mock fixtures for rclpy & ROS msgs
│   ├── test_server.py                # Server lifecycle and depth streaming test
│   └── test_services.py              # Unit tests for parameter, TF, and sensor logic
├── package.xml                       # ROS 2 package manifest
├── requirements.txt                  # Python dependencies (grpcio, protobuf, etc.)
├── setup.cfg                         # Package installation config
├── setup.py                          # Setuptools installation file
└── README.md                         # Main package overview & quickstart
```

---

## 2. Core Architectural Patterns

### 2.1 ROS 2 Singleton Handle (`RosHandle`)
`marus2_ros_adapter.grpc_utils.ros_handle.RosHandle` provides a centralized singleton access point for the underlying ROS 2 node (`synthetic_data`).

- Access the node anywhere using:
  ```python
  from marus2_ros_adapter.grpc_utils.ros_handle import RosHandle
  rh = RosHandle()
  node = rh.node
  ```
- **Time helper**: `rh.get_time()` returns a valid `builtin_interfaces.msg.Time` stamped with the current ROS time (using simulation time `/clock` if `use_sim_time` is enabled).

### 2.2 Thread-Safe Publisher Registry (`RosPublisherRegistry`)
Because gRPC calls execute inside thread pool workers concurrently, publishers must never be created or looked up via race-prone dictionary access. Always use:
```python
from marus2_ros_adapter.grpc_utils.ros_publisher_registry import RosPublisherRegistry

pub = RosPublisherRegistry.get_publisher(
    topic_name="my_sensor",
    msg_type=MyRosMsgType,
    queue_size=10,
    latched=False
)
pub.publish(msg)
```

### 2.3 Streaming from ROS 2 to gRPC (`Streamer`)
When delivering a stream of ROS 2 subscriber messages back to a gRPC client (e.g. `/tf` or `/markers`):
1. Wrap the stream in `marus2_ros_adapter.grpc_utils.topic_streamer.Streamer`.
2. The streamer automatically manages a bounded queue, drops old messages if the gRPC client is slow, and monitors `context.is_active()` to cleanly exit when the client disconnects.

---

## 3. How-To Guides

### 3.1 Adding a New Sensor Stream

To add support for a new sensor type (e.g. Magnetometer or Fluorometer):

#### Step 1: Ensure Protobuf Definition Exists
Verify that the message and RPC definition exist in `marus2_ros_adapter/marus2_proto/sensor_streaming.proto`. For example:
```protobuf
rpc StreamMagnetometerSensor (stream MagnetometerSensor) returns (std.Empty);
```
*(If you need to compile updated proto files, see [Section 4](#4-protobuf-compilation--updates).)*

#### Step 2: Add the Publisher Callback in `services/sensor_callbacks.py`
Add a dedicated conversion and publish function:
```python
from sensor_msgs.msg import MagneticField
from marus2_ros_adapter.grpc_utils.ros_publisher_registry import RosPublisherRegistry
from marus2_ros_adapter.grpc_utils.ros_handle import RosHandle

def publish_magnetometer(data):
    """
    Translates a Magnetometer protobuf message and publishes to ROS 2.
    """
    rh = RosHandle()
    topic = getattr(data, 'address', 'magnetic_field')
    frame_id = getattr(data, 'frame_id', 'magnetometer_link')

    msg = MagneticField()
    msg.header.stamp = rh.get_time()
    msg.header.frame_id = frame_id
    msg.magnetic_field.x = float(data.x)
    msg.magnetic_field.y = float(data.y)
    msg.magnetic_field.z = float(data.z)

    pub = RosPublisherRegistry.get_publisher(topic, MagneticField, queue_size=10)
    pub.publish(msg)
```

#### Step 3: Implement the RPC in `services/sensor_streaming.py`
In `SensorStreamingServicer`, implement the streaming RPC:
```python
def StreamMagnetometerSensor(self, request_iterator, context):
    for sensor_data in request_iterator:
        if not context.is_active():
            break
        publish_magnetometer(sensor_data)
    return std_pb2.Empty()
```
> [!IMPORTANT]
> Always return `std_pb2.Empty()`, check `context.is_active()`, and iterate through `request_iterator`.

#### Step 4: Add Unit Tests
Add a test in `tests/test_services.py` validating that incoming protobuf messages are correctly converted and passed to the publisher.

---

### 3.2 Adding a Control / Actuator Service

When receiving control signals from ROS 2 and streaming them to Unity (e.g. thruster setpoints or waypoint commands):

1. **In Unity / Proto**: Define a server-streaming RPC in `remote_control.proto`:
   ```protobuf
   rpc StreamThrusterCommands (std.Empty) returns (stream ThrusterCommand);
   ```
2. **In `services/remote_control.py`**:
   - Set up a ROS 2 subscriber using `RosHandle().create_subscription`.
   - Use `Streamer` to buffer incoming ROS messages and yield them to the gRPC stream.
   - Guard the loop with `context.is_active()`.

---

## 4. Protobuf Compilation & Updates

Protobuf messages are defined in the companion [marus2-proto](https://github.com/MARUSimulator/marus2-proto) repository, linked as a git submodule in `marus2_ros_adapter/marus2_proto`.

### 4.1 Updating the Submodule
```bash
cd ~/marus_ws/src/marus2_ros_adapter
git submodule update --remote marus2_ros_adapter/marus2_proto
```

### 4.2 Compiling Protobuf and gRPC Stubs
To compile the `.proto` files into Python stubs:

```bash
cd ~/marus_ws/src/marus2_ros_adapter/marus2_ros_adapter/marus2_proto

# Compile all protos in the directory
python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    *.proto
```

### 4.3 Python 3.12 & Protobuf Runtime Compatibility
In Ubuntu 24.04 (ROS 2 Jazzy) and Python 3.12+, `protobuf >= 4.x` requires descriptors to match runtime versions. To prevent `TypeError: Descriptors cannot be created directly`, `marus2_ros_adapter/__init__.py` automatically configures:
```python
import os
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
```
Keep this fallback in place to maintain seamless compatibility across standard distributions.

---

## 5. Cross-Distribution Best Practices (Galactic to Rolling)

To maintain 100% compatibility across **Galactic**, **Humble**, **Iron**, **Jazzy**, and **Rolling** without maintaining separate branches, adhere to these rules:

1. **Pure `rclpy` APIs**:
   - Never import ROS 1 modules (`rospy`, `genpy`, `rospkg`).
   - Use standard `rclpy.node.Node` APIs.

2. **Parameter Declaration**:
   - In ROS 2, parameters must be declared before retrieval.
   - To safely handle default parameters without throwing `ParameterAlreadyDeclaredException`, use the safe pattern established in `RosHandle`:
     ```python
     if not self.node.has_parameter(name):
         self.node.declare_parameter(name, default_value)
     return self.node.get_parameter(name).value
     ```

3. **Time Messages & Clocks**:
   - Avoid deprecated time conversion functions.
   - Always stamp messages using `rh.get_time()`, which constructs a `builtin_interfaces.msg.Time` object:
     ```python
     from builtin_interfaces.msg import Time
     now = node.get_clock().now()
     t = Time()
     t.sec = int(now.nanoseconds // 1000000000)
     t.nanosec = int(now.nanoseconds % 1000000000)
     ```

4. **NumPy 2.0+ Compatibility (Python 3.12 / Ubuntu 24.04)**:
   - Avoid deprecated NumPy functions such as `np.fromstring()`.
   - Always use `np.frombuffer(raw_bytes, dtype=...)`.

---

## 6. Testing & Quality Assurance

### 6.1 Running the Unit Tests
The test suite in `tests/` uses offline mock objects, meaning tests can run in any environment with `pytest` installed, even without a sourced ROS 2 installation:

```bash
pytest tests/ -v
```

### 6.2 Test Suite Structure
- **`tests/conftest.py`**: Provides mocked `rclpy`, `builtin_interfaces`, `sensor_msgs`, `std_msgs`, and `geometry_msgs`. Sets `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`.
- **`tests/test_server.py`**: Boots an in-process gRPC test server with `SensorStreamingServicer` and verifies client-streaming RPC calls over a loopback socket.
- **`tests/test_services.py`**:
  - Tests parameter server `GetParameter` and `SetParameter` (including booleans and falsy values).
  - Tests `VisualizationServicer` marker array extend logic.
  - Tests static TF deduplication in `FrameService`.
  - Tests DVL callback velocity extraction.

### 6.3 Code Quality & Formatting
Before submitting pull requests:
```bash
# Format code
black marus2_ros_adapter tests

# Lint check
flake8 marus2_ros_adapter tests --max-line-length=120
```

