from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 🎥 启动 Orbbec 摄像头驱动（你也可以写成另一个 launch include）
        Node(
            package='orbbec_camera',
            executable='orbbec_camera_node',
            name='camera',
            output='screen',
            parameters=[{'device_type': 'DABAI_DCW2'}],
        ),

        # 🎙️ Whisper 节点
        Node(
            package='piper_voice',
            executable='whisper_node',
            name='whisper_node',
            output='screen'
        ),

        # 🧠 大模型解析节点（LLM via Ollama）
        Node(
            package='piper_llm',
            executable='llm_node',
            name='llm_node',
            output='screen'
        ),

        # 🎯 YOLO + 深度图 感知节点
        Node(
            package='piper_vision',
            executable='object_detector',
            name='object_detector',
            output='screen'
        ),

        # 🔁 坐标系转换节点 TF
        Node(
            package='piper_tf',
            executable='tf_transformer',
            name='tf_transformer',
            output='screen'
        ),

        # 🤖 MoveIt 控制节点（抓取）
        Node(
            package='piper_control',
            executable='grasp_server',
            name='grasp_server',
            output='screen'
        ),

        # 🖼️ 启动 RViz
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', '/home/zzb/zzb_HDD/Project/piper/src/piper_moveit/config/demo.rviz']  # 可根据你配置修改
        ),
    ])
