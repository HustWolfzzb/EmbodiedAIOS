import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import requests
import json

class OllamaChat():
    def __init__(self, system_message="你现在是一个四轮小车底座+六自由度夹爪机械臂的大脑，这一系统具备有视觉功能，语音识别与输出功能、机械臂控制功能，你的主要任务是充当指令到分解的任务的转换员，将从语音系统转换的指令转化为各个子系统的细分任务。",
                 url="http://162.105.175.7:11434/api/chat", model_name="deepseek-r1:14b"):
        self.url = url
        self.model_name = model_name
        self.system_message = {
            "role": "system",
            "content": f"{system_message}"
        }

    def ouput_response(self, response, stream=False, is_chat=True):
        if stream:
            return_text = ''
            for chunk in response.iter_content(chunk_size=None):
                if chunk:
                    if is_chat:
                        text = json.loads(chunk.decode('utf-8'))['message']['content']
                    else:
                        text = json.loads(chunk.decode('utf-8'))['response']
                    return_text += text
                    print(text, end='', flush=True)
        else:
            if is_chat:
                return_text = ''.join([
                    json.loads(line)['message']['content']
                    for line in response.text.split('\n') if line.strip()
                ])
            else:
                return_text = ''.join([
                    json.loads(line)['response']
                    for line in response.text.split('\n') if line.strip()
                ])
        return return_text

    def chat(self, prompt, message=[], stream=False, temperature=None):
        if not message:
            message.append(self.system_message)
        message.append({"role": "user", "content": prompt + '. 如果对话是一条指令，请你仅以json格式返回, json类似{"task": "抓取", "object": "红色杯子", "location": "table"……}'})
        data = {
            "model": self.model_name,
            "messages": message 
        }
        if temperature is not None:
            data["options"] = {"temperature": temperature}
        headers = {"Content-Type": "application/json"}
        responses = requests.post(self.url, headers=headers, json=data, stream=stream)
        return_text = self.ouput_response(responses, stream)
        message.append({"role": "assistant", "content": return_text})
        return return_text, message

class LLMNode(Node):
    def __init__(self):
        super().__init__('llm_node')
        self.sub = self.create_subscription(String, 'voice_command', self.cb, 10)
        self.pub = self.create_publisher(String, 'parsed_plan', 10)
        self.chatbot = OllamaChat()
        self.msg_history = []
        self.get_logger().info("🧠 LLM Node Ready - 使用 DeepSeek-R1-14B")

    def cb(self, msg: String):
        prompt = msg.data.strip()
        self.get_logger().info(f"🧠 接收到语音指令: {prompt}")
        try:
            answer, self.msg_history = self.chatbot.chat(prompt, self.msg_history, stream=False)
            plan_msg = String()
            plan_msg.data = answer
            self.pub.publish(plan_msg)
            self.get_logger().info(f"📤 发布解析结果: {answer}")
        except Exception as e:
            self.get_logger().error(f"❌ 调用 LLM 失败: {e}")

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(LLMNode())
    rclpy.shutdown()
