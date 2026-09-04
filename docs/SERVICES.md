# Services & Endpoints Reference

This document provides a complete reference for all gRPC services implemented in `marus2_ros_adapter`, including RPC method signatures, Protobuf message types, corresponding ROS 2 topics, and ROS 2 message definitions.

---

## 1. Summary of Services

| Service Name | Protobuf Definition | Direction | Primary Purpose |
| :--- | :--- | :--- | :--- |
| **`SensorStreaming`** | `sensor_streaming.proto` | Unity -> ROS 2 (Client-stream) | Ingests sensor data from Unity and publishes to ROS 2 topics. |
| **`FrameService`** | `tf.proto` | Bidirectional | Synchronizes coordinate transforms between Unity and ROS 2 `/tf`. |
| **`SimulationControl`** | `simulation_control.proto` | Unity -> ROS 2 | Synchronizes simulation time via the ROS 2 `/clock` topic. |
| **`ParameterServer`** | `parameter_server.proto` | Bidirectional | Reads and updates ROS 2 node parameters over gRPC. |
| **`RemoteControl`** | `remote_control.proto` | ROS 2 -> Unity (Server-stream) | Streams thruster force commands to simulated vehicles. |
| **`Visualization`** | `visualization.proto` | ROS 2 -> Unity (Server-stream) | Streams RViz markers and marker arrays to Unity for rendering. |
| **`AcousticTransmission`** | `acoustic_transmission.proto` | Bidirectional | Simulates underwater acoustic modem communications. |
| **`PingService`** | `ping.proto` | Bidirectional (Unary) | Connection heartbeat and health verification. |

---

## 2. SensorStreaming Service

All client-streaming methods accept an address string (e.g. `vehicle1/camera`) within the request message. The adapter automatically publishes the data onto the corresponding ROS 2 topic.

### 2.1 `StreamCameraSensor`
- **RPC Signature**: `StreamCameraSensor(stream CameraStreamingRequest) returns (std.Empty)`
- **Request Fields**:
  - `image`: Raw RGB image bytes, height, width.
  - `compressedImage`: JPEG/PNG compressed image bytes and format.
  - `address`: Target ROS topic.
- **Published ROS 2 Topics**:
  - `/<address>` (`sensor_msgs/msg/Image`, encoding `bgr8`)
  - `/<address>/compressed` (`sensor_msgs/msg/CompressedImage`)

### 2.2 `StreamSonarImage`
- **RPC Signature**: `StreamSonarImage(stream CompressedImageStreamingRequest) returns (std.Empty)`
- **Published ROS 2 Topic**: `/<address>` (`sensor_msgs/msg/Image`)

### 2.3 `StreamImuSensor`
- **RPC Signature**: `StreamImuSensor(stream ImuStreamingRequest) returns (std.Empty)`
- **Request Fields**: `orientation`, `angularVelocity`, `linearAcceleration`, `header`.
- **Published ROS 2 Topic**: `/<address>` (`sensor_msgs/msg/Imu`)

### 2.4 `StreamPoseSensor`
- **RPC Signature**: `StreamPoseSensor(stream PoseStreamingRequest) returns (std.Empty)`
- **Published ROS 2 Topic**: `/<address>` (`geometry_msgs/msg/PoseWithCovarianceStamped`)

### 2.5 `StreamDepthSensor`
- **RPC Signature**: `StreamDepthSensor(stream DepthStreamingRequest) returns (std.Empty)`
- **Behavior**: Reads Z position and inverts it (`-z`) to match positive depth convention.
- **Published ROS 2 Topic**: `/<address>` (`geometry_msgs/msg/PoseWithCovarianceStamped`)

### 2.6 `StreamDvlSensor`
- **RPC Signature**: `StreamDvlSensor(stream DvlStreamingRequest) returns (std.Empty)`
- **Request Fields**: `velocity` (Vector3), `velocityCovariance`, `altitude`.
- **Published ROS 2 Topic**: `/<address>` (`geometry_msgs/msg/TwistWithCovarianceStamped`)

### 2.7 `StreamGnssSensor`
- **RPC Signature**: `StreamGnssSensor(stream GnssStreamingRequest) returns (std.Empty)`
- **Request Fields**: `latitude`, `longitude`, `altitude`, `status`, `service`.
- **Published ROS 2 Topic**: `/<address>` (`sensor_msgs/msg/NavSatFix`)

### 2.8 `StreamAisSensor`
- **RPC Signature**: `StreamAisSensor(stream AISStreamingRequest) returns (std.Empty)`
- **Published ROS 2 Topic**: `/<address>` (`uuv_sensor_msgs/msg/AISPositionReport`)

### 2.9 `StreamPointCloud` & `StreamPointCloud2`
- **RPC Signatures**:
  - `StreamPointCloud(stream PointCloudStreamingRequest) returns (std.Empty)`
  - `StreamPointCloud2(stream PointCloud2StreamingRequest) returns (std.Empty)`
- **Published ROS 2 Topics**:
  - `/<address>` (`sensor_msgs/msg/PointCloud` or `sensor_msgs/msg/PointCloud2`)

### 2.10 `RequestPointCloud2`
- **RPC Signature**: `RequestPointCloud2(std.StandardRequest) returns (stream PointCloud2StreamingRequest)`
- **Behavior**: Server-streaming endpoint allowing Unity to stream ROS 2 `PointCloud2` messages published by external nodes.

---

## 3. FrameService (TF)

Synchronizes transform trees between Unity and ROS 2.

### 3.1 `GetAllFrames`
- **RPC Signature**: `GetAllFrames(std.Empty) returns (tf.TfFrameList)`
- **Behavior**: Returns a single snapshot containing all current dynamic and static transforms stored by the adapter.

### 3.2 `StreamAllFrames`
- **RPC Signature**: `StreamAllFrames(std.Empty) returns (stream tf.TfFrameList)`
- **Behavior**: Continuously streams transform frames to Unity at 100 Hz. Monitors client connection state to prevent thread leaks.

### 3.3 `PublishFrame`
- **RPC Signature**: `PublishFrame(stream tf.TfFrame) returns (std.Empty)`
- **Behavior**: Ingests transforms from Unity and broadcasts them to the ROS 2 `/tf` topic as `tf2_msgs/msg/TFMessage`.

---

## 4. SimulationControl Service

Enables lock-step simulation execution where the simulator dictates simulation time to ROS 2.

### 4.1 `SetStartTime`
- **RPC Signature**: `SetStartTime(simulation_control.SetStartTimeRequest) returns (simulation_control.SetStartTimeResponse)`
- **Behavior**: Initializes the clock and publishes the start timestamp to `/clock` (`rosgraph_msgs/msg/Clock`).

### 4.2 `Step`
- **RPC Signature**: `Step(simulation_control.StepRequest) returns (simulation_control.StepResponse)`
- **Behavior**: Advances simulation time by broadcasting the current simulated seconds and nanoseconds to `/clock`.

---

## 5. ParameterServer Service

Provides remote reading and writing of parameters configured on the adapter's ROS 2 node.

### 5.1 `GetParameter`
- **RPC Signature**: `GetParameter(parameterserver.GetParamRequest) returns (parameterserver.ParamValue)`
- **Supported Types**: `valueBool`, `valueInt`, `valueDouble`, `valueStr`.

### 5.2 `SetParameter`
- **RPC Signature**: `SetParameter(parameterserver.SetParamRequest) returns (std.Empty)`
- **Behavior**: Automatically declares and updates the parameter value on the ROS 2 node. Supports falsy values (`0`, `0.0`, `False`, `""`).

---

## 6. RemoteControl Service

### 6.1 `ApplyForce`
- **RPC Signature**: `ApplyForce(remote_control.ForceRequest) returns (stream remote_control.ForceResponse)`
- **Subscribed ROS 2 Topic**: `/<address>` (`std_msgs/msg/Float32MultiArray`)
- **Behavior**: Streams thruster command arrays to Unity with non-blocking buffer queues.

---

## 7. Visualization Service

Allows Unity to visualize ROS 2 markers published by planner or perception nodes.

### 7.1 `SetMarker`
- **RPC Signature**: `SetMarker(visualization.MarkerRequest) returns (stream visualization.Marker)`
- **Subscribed ROS 2 Topic**: `/<address>` (`visualization_msgs/msg/Marker`)

### 7.2 `SetMarkerArray`
- **RPC Signature**: `SetMarkerArray(visualization.MarkerRequest) returns (stream visualization.MarkerArray)`
- **Subscribed ROS 2 Topic**: `/<address>` (`visualization_msgs/msg/MarkerArray`)

---

## 8. AcousticTransmission Service

Simulates underwater acoustic modems (e.g. NanoModem).

### 8.1 `StreamAcousticRequests`
- **RPC Signature**: `StreamAcousticRequests(acoustictransmission.CommandRequest) returns (stream acoustictransmission.AcousticRequest)`
- **Subscribed ROS 2 Topic**: `/<address>` (`uuv_sensor_msgs/msg/AcousticModemRequest`)

### 8.2 `ReturnAcousticPayload`
- **RPC Signature**: `ReturnAcousticPayload(acoustictransmission.AcousticResponse) returns (std.Empty)`
- **Behavior**: Unary RPC delivering modem replies or ranges from Unity and publishing them to ROS 2 as `AcousticModemPayload` or `AcousticModemRange`.

