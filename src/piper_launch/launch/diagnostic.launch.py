from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import LogInfo

def try_node(pkg, exe, name=None):
    return [
        LogInfo(msg=f'🔍 正在测试节点: {pkg}/{exe}'),
        Node(
            package=pkg,
            executable=exe,
            name=name or exe,
            output='screen',
            parameters=[],
            emulate_tty=True
        )
    ]

def generate_launch_description():
    return LaunchDescription(
        try_node('piper_voice', 'whisper_node') +
        try_node('piper_llm', 'llm_node') +
        try_node('piper_vision', 'object_detector') +
        try_node('piper_tf', 'tf_transformer') +
        try_node('piper_control', 'grasp_server')
    )
