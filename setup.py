from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'marus2_ros_adapter'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['tests*']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*_launch.py'))),
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.yaml'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='labust',
    maintainer_email='labust@fer.hr',
    description='Bridges and translates messages between ROS 2 and Unity MARUS simulator using gRPC',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            f'server = {package_name}.server:main',
        ],
    },
)
