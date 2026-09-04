from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'server_ip',
            default_value='0.0.0.0',
            description='IP address for the gRPC server to bind to'
        ),
        DeclareLaunchArgument(
            'server_port',
            default_value='30052',
            description='Port for the gRPC server to listen on'
        ),
        Node(
            package='marus2_ros_adapter',
            executable='server',
            name='marus2_ros_adapter',
            output='screen',
            parameters=[{
                'server_ip': LaunchConfiguration('server_ip'),
                'server_port': LaunchConfiguration('server_port'),
            }]
        )
    ])
