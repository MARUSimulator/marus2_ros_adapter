# System Architecture

This document provides a comprehensive explanation of the `marus2_ros_adapter` architecture, its concurrency model, communication flow, and design patterns.

---

## 1. Design Rationale: Why gRPC?

Simulating marine robotics in Unity requires streaming rich, high-frequency, and large-payload sensor data (e.g. RGB camera feeds at 30+ FPS, point clouds with tens of thousands of points, multi-beam sonar arrays, and IMU data at 100+ Hz).

While running native ROS 2 client libraries in Unity via C# (e.g. `ros2cs` or DDS bindings) is possible, it presents severe challenges:
1. **DDS Native Dependencies**: Cross-compiling DDS implementations (FastDDS, CycloneDDS) for Unity's Mono/IL2CPP runtimes on different platforms is fragile.
2. **Payload Serialization Overhead**: Serialization in pure C# for ROS 2 messages is often slower than protobuf compiled code.
3. **Network Boundary**: gRPC operates over standard HTTP/2 (TCP), making it trivial to run Unity on a powerful Windows or Linux rendering workstation while ROS 2 runs in a Linux Docker container, VM, or companion computer on the same LAN without DDS multicast discovery issues.

`marus2_ros_adapter` acts as a **bridge process** that terminates the gRPC connection from Unity and translates data directly into native ROS 2 topics, services, and transforms.

---

## 2. Architectural Components

```
+-------------------------------------------------------------+
|               Unity Simulation Engine (C#)                  |
|  - Sensor Generators (Camera, Sonar, Lidar, IMU, DVL)       |
|  - Vehicle Dynamics (Thrusters, Hydrodynamics, Buoyancy)     |
|  - gRPC Client Stubs (Generated from marus2-proto)         |
+-------------------------------------------------------------+
                               |
               gRPC Channels (TCP / HTTP/2)
                               |
                               v
+-------------------------------------------------------------+
|                  marus2_ros_adapter                         |
|                                                             |
|  [gRPC ThreadPool (up to 100 workers)]                      |
|    |                                                        |
|    +--> SensorStreamingServicer                             |
|    |      - StreamCameraSensor    --> publish_image         |
|    |      - StreamImuSensor       --> publish_imu           |
|    |      - StreamDvlSensor       --> publish_dvl           |
|    |      - StreamPointCloud2     --> publish_pointcloud2   |
|    |                                                        |
|    +--> FrameService (TfServicer)                           |
|    |      - StreamAllFrames (gRPC -> Unity)                 |
|    |      - PublishFrame (Unity -> ROS /tf)                 |
|    |                                                        |
|    +--> SimulationControlServicer                           |
|    |      - Step / SetStartTime   --> /clock                |
|    |                                                        |
|    +--> RemoteControlServicer                               |
|    |      - ApplyForce (ROS /forces -> Unity)               |
|    |                                                        |
|    +--> ParameterServerServicer                             |
|           - GetParameter / SetParameter                     |
|                                                             |
|  [Thread-Safe Infrastructure]                                |
|    - RosPublisherRegistry (Lock-protected publisher cache)  |
|    - Streamer (Queue-backed server-streaming helper)        |
|    - Extensions (Fast ROS <-> Proto conversions)            |
|                                                             |
|  [ROS 2 Node (rclpy: 'synthetic_data')]                     |
|    - Publishers (/camera, /imu, /dvl, /tf, /clock)          |
|    - Subscribers (/tf, /tf_static, /forces, /markers)       |
+-------------------------------------------------------------+
                               |
                       DDS Middleware
                               |
                               v
+-------------------------------------------------------------+
|                   ROS 2 Ecosystem                           |
|  - Nav2 Navigation Stack      - RViz2 Visualization         |
|  - SLAM & State Estimation    - LABUST Control Algorithms   |
+-------------------------------------------------------------+
```

---

## 3. Concurrency & Threading Model

The adapter operates across two distinct concurrency paradigms:

### 3.1 gRPC ThreadPoolExecutor
- The gRPC server runs on a `concurrent.futures.ThreadPoolExecutor(max_workers=100)`.
- Each incoming client connection or streaming RPC is dispatched to a background worker thread.
- Multiple sensors stream concurrently without blocking each other. For instance, high-bandwidth camera streams do not delay high-rate IMU callbacks.

### 3.2 ROS 2 Node Spinning
- The ROS 2 node (`synthetic_data`) is initialized using `rclpy`.
- `rh.spin()` runs the executor event loop, handling topic subscriptions, timers, and service requests.

### 3.3 Thread Safety Bridges
Because gRPC worker threads interact with ROS 2 publishers and subscribers concurrently, thread safety is enforced via:
1. **`RosPublisherRegistry`**:
   - Uses a `threading.Lock()` when registering or retrieving publishers.
   - Ensures multiple gRPC threads publishing to the same topic do not create duplicate publishers or corrupt the internal publisher dictionary.
2. **`Streamer`**:
   - Manages an internal `queue.Queue(maxsize=100)` per client/topic pair.
   - Discards older frames safely under `queue.Full` conditions so that ROS callbacks are never blocked by slow network clients.
   - Monitors `context.is_active()` to immediately terminate generators and prevent thread leaks when clients disconnect.

---

## 4. Communication Flows

### 4.1 Ingress Flow (Simulator -> ROS 2)
```
[Unity Sensor]
       | (Protobuf message over gRPC stream)
       v
[gRPC Servicer: e.g. StreamDepthSensor]
       |
       v
[Sensor Callback: publish_depth]
       |
       v  (Coordinates inverted, ROS message created)
[RosPublisherRegistry.get_publisher()]
       |
       v
[rclpy Publisher.publish()] --> DDS --> ROS 2 Network
```

### 4.2 Egress Flow (ROS 2 -> Simulator)
```
ROS 2 Topic: e.g. /tf or vehicle control commands
       |
       v
[rclpy Subscription Callback]
       |
       v
[Streamer Client Queue (Bounded, Non-blocking)]
       |
       v
[gRPC Server Streaming Generator (yields response)]
       |
       v (Protobuf over HTTP/2)
[Unity Simulator C# Consumer]
```

---

## 5. Coordinate Frame Conventions

Marine robotics applications must carefully reconcile the differences between Unity and ROS coordinate conventions:

| Convention | Unity Engine | ROS 2 (REP 103) |
| :--- | :--- | :--- |
| **Coordinate Handedness** | **Left-handed** | **Right-handed** |
| **X Axis** | Right | Forward |
| **Y Axis** | Up | Left |
| **Z Axis** | Forward | Up |
| **Depth Convention** | Negative Y or positive Z (custom) | Positive Z down (NED) or negative Z up (ENU) |

### Transform Mapping in `marus2_ros_adapter`
- Depth measurements: Unity positive depth (underwater) is mapped to standard ROS representation:
  ```python
  pose.pose.pose.position = Point(x=0.0, y=0.0, z=-float(request.data.pose.pose.position.z))
  ```
- Conversions in [`extensions.py`](file:///c:/grpc_ros_adapter/marus2_ros_adapter/grpc_utils/extensions.py) provide direct scalar translation between `geometry_msgs` and `geometry_pb2`.

