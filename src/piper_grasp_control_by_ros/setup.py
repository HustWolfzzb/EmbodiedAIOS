from setuptools import find_packages, setup

package_name = 'piper_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='zzb',
    maintainer_email='zzb@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        'grasp_server = piper_control.grasp_server:main',
        'gripper_controller_node = piper_control.gripper_controller_node:main',
        ],
    },
)
