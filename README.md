# marus2_ros_adapter

[![ROS 2](https://img.shields.io/badge/ROS_2-Humble%20%7C%20Jazzy%20%7C%20Rolling%20%7C%20Galactic-blue.svg)](https://docs.ros.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.8%20%7C%203.10%20%7C%203.12-green.svg)](https://www.python.org/)

## 1. Overview

`marus2_ros_adapter` is a high-performance gRPC bridge between the **MARUS (Marine Robotics Unity Simulator)** and **ROS 2**. It enables bidirectional communication between Unity-based vehicle simulations and ROS 2 autonomy stacks:

- **Simulator -> ROS 2 (Sensors & States)**: Streams visual cameras, imaging sonars, DVL, IMU, depth, GNSS, AIS, PointCloud, and PointCloud2 sensor data from Unity into native ROS 2 topics.
- **ROS 2 -> Simulator (Actuation & Control)**: Streams motor control commands, vehicle thruster forces, and navigation goals from ROS 2 back into Unity.
- **Clock & Synchronization**: Synchronizes simulation time with ROS 2 via `/clock` step requests.
- **TF Frame Synchronization**: Bidirectional transform broadcasting between Unity coordinate frames and ROS 2 TF trees (`/tf`, `/tf_static`).
- **Parameter & Visualization Management**: Provides gRPC parameter querying/setting and ROS 2 Marker/MarkerArray visualization streaming.

> [!NOTE]
> **Universal ROS 2 Support**: This package is engineered to run seamlessly across all modern ROS 2 distributions including **Humble (LTS)**, **Jazzy (LTS)**, **Rolling**, and **Galactic** using a single unified codebase.

---

## 2. System Architecture

```
+-------------------------------------------------------------+
|                 MARUS Simulator (Unity C#)                  |
|  - Physics Engine      - Sensor Renderers      - Underwater |
+-------------------------------------------------------------+
                              |
                     gRPC Channel (HTTP/2)
                     Protobuf Messages
                              |
                              v
+-------------------------------------------------------------+
|            marus2_ros_adapter (ROS 2 Python)                |
|  +---------------------+      +--------------------------+  |
|  |    gRPC Servicers   |      |      ROS 2 Handlers      |  |
|  |  - SensorStreaming  | <==> |  - Topic Publishers      |  |
|  |  - FrameService     |      |  - Topic Subscribers     |  |
|  |  - SimControl       |      |  - Transform Broadcaster |  |
|  |  - RemoteControl    |      |  - Service Clients       |  |
|  +---------------------+      +--------------------------+  |
+-------------------------------------------------------------+
                              |
                          DDS / ROS 2
                              |
                              v
+-------------------------------------------------------------+
|               ROS 2 Navigation & Autonomy Stack             |
|   (Nav2, SLAM, LABUST NGC Controllers, RViz2, Custom Nodes)  |
+-------------------------------------------------------------+
```

For detailed architecture diagrams and concurrency models, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 3. Installation & Prerequisites

### 3.1 Prerequisites
- **Operating System**: Ubuntu 22.04 LTS or Ubuntu 24.04 LTS (Windows with Python 3.10+ supported for development/testing).
- **ROS 2**: Humble Hawksbill, Jazzy Jalisco, Rolling Ridley, or Galactic.
- **Git**: With submodule support.

### 3.2 Workspace Setup

1. Create or navigate to your ROS 2 colcon workspace:
   ```bash
   mkdir -p ~/marus2_ws/src
   cd ~/marus2_ws/src
   ```

2. Clone this repository:
   ```bash
   git clone https://github.com/MARUSimulator/marus2_ros_adapter.git
   cd marus2_ros_adapter
   ```

3. Initialize and pull the required protobuf submodules:
   ```bash
   git submodule update --init --recursive
   ```

4. Clone companion message packages (such as `uuv_sensor_msgs`):
   ```bash
   cd ~/marus2_ws/src
   git clone -b ros2 https://github.com/labust/uuv_sensor_msgs.git
   ```

5. Install dependencies via `rosdep`:
   ```bash
   cd ~/marus2_ws
   # Run once if rosdep has not been initialized on this machine:
   # sudo rosdep init
   rosdep update
   rosdep install --from-paths src --ignore-src -r -y
   ```

   > [!NOTE]
   > All required Python and ROS dependencies (such as `python3-grpcio`, `python3-protobuf`, `python3-opencv`, `python3-yaml`, and `cv_bridge`) are declared in `package.xml` and installed via `rosdep`. If you are developing in a standalone Python virtual environment without ROS 2, you can install via `pip install -r requirements.txt`.

---

## 4. Building the Package

1. Source your underlying ROS 2 installation (if not already sourced in your terminal):
   ```bash
   source /opt/ros/<ros2-distro>/setup.bash   # e.g., lyrical, jazzy, humble, or rolling
   ```

2. Build the workspace using `colcon`:
   ```bash
   cd ~/marus2_ws
   colcon build --symlink-install --packages-up-to marus2_ros_adapter
   ```
   *(Or simply run `colcon build --symlink-install` to build all packages in the workspace including `uuv_sensor_msgs`).*

3. Source the workspace overlay:
   ```bash
   source install/setup.bash
   ```

---

## 5. Running the Adapter

### 5.1 Quick Launch

Launch the adapter with default settings (server listening on `0.0.0.0:30052`):

```bash
ros2 launch marus2_ros_adapter ros2_server_launch.py
```

### 5.2 Configuring Port and IP

You can customize the listening IP address and port via launch arguments:

```bash
ros2 launch marus2_ros_adapter ros2_server_launch.py server_ip:=127.0.0.1 server_port:=30055
```

Alternatively, configure defaults in `config/server.yaml`:
```yaml
server_ip: "0.0.0.0"
server_port: 30052
```

### 5.3 Direct Node Execution

You can also run the server node directly using the ROS 2 CLI:

```bash
ros2 run marus2_ros_adapter server --ros-args -p server_port:=30052
```

---

## 6. Running Tests

The test suite includes offline mocks, allowing tests to run in any Python environment (with or without ROS 2 sourced):

```bash
cd ~/marus2_ws/src/marus2_ros_adapter
pytest tests/ -v
```

---

## 7. Documentation Index

Detailed documentation is available in the `docs/` folder:

| Document | Description |
| :--- | :--- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | In-depth architecture, data flow, threading model, and coordinate system conventions. |
| [docs/SERVICES.md](docs/SERVICES.md) | Complete reference of all gRPC services, endpoints, ROS topics, and message types. |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Development guidelines, adding new sensors, regenerating protobufs, and testing. |

---

## 8. Related Repositories

- **[marus2-core](https://github.com/MARUSimulator/marus2-core)**: Unity package containing core simulator assets, physics, and sensor implementations.
- **[marus2-proto](https://github.com/MARUSimulator/marus2-proto)**: Protobuf message and service definitions.
- **[marus2-example](https://github.com/MARUSimulator/marus2-example)**: Example scenes and integration demonstrations.
- **[uuv_sensor_msgs](https://github.com/labust/uuv_sensor_msgs)**: Underwater sensor message definitions for ROS 2.

---

## 9. License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.