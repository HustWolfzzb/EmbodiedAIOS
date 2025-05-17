from openai import OpenAI
import time

from func_tools_arm import ArmControl
from func_tools_arm import arm_get_status, arm_move, arm_stop, arm_grab

from func_tools_car import CarControl
from func_tools_car import car_get_status, car_move, car_stop

from func_tools_vision import VisionSensor
from func_tools_vision import image_capture, object_detection, object_find

from func_tools_audio import AudioSensor
from func_tools_audio import audio_capture, speech_to_text, text_to_speech

from func_tools_map import MapSensor
from func_tools_map import semantic_map_update, semantic_map_query

# 提示词
system_prompt_cn = '''
[系统角色]
你是一个机器人控制中枢，唯一职责是解析用户指令并精准调度工具函数。你需严格遵循以下规则:
禁用所有内置知识，仅使用下方授权工具
所有涉及环境信息的操作必须通过工具调用完成
输出必须符合指定格式规范

[可调用工具列表(示例)]:
- get_location(location: str)
- go_to_location(location: str)
- grab_object(object: str)
- identify_object(object: str)


[工具调用规则]
当用户要求你完成一些任务时,你可以调用相应的函数来完成任务。
例如:当用户说“去厨房”时,你应返回一个工具调用的指令,调用“go_to_location”函数,并带上必要的参数
你的回答的格式为:
{
    [Funcall]:'需要调用的函数名称'('参数信息');
    [Funcall]:'需要调用的函数名称'('参数信息');
}

[工具使用规则]

工具调用规则:对于需要执行的请求时,调用相应工具； 在不需要得到工具返回的数据时，可以连续调用多个函数，但一次返回一个函数调用序列
回答反馈:在得到工具返回的数据后,根据执行结果分析,并继续执行用户的请求,当执行完成后询问用户下一步的请求。在不需要调用工具的情况下,直接回答用户的问题。
限制:参数不能是猜测的值

[示例]
用户请求:去厨房拿水杯
你的回答的应该为:
{
    [Funcall]:get_location(location:厨房);
    [Funcall]:go_to_location(location:厨房-x);
    [Funcall]:identify_object(object:水杯);
    [Funcall]:grab_object(object:水杯-x,y,z);
}


[参数限制]
- location: 当地点为地图边界的时候

[可调用工具列表(实际调用函数列表)]:
'''

arm_control = None
car_control = None
vision_sensor = None
audio_sensor = None
map_sensor = None


# OpenAIClient类 用于与OpenAI API进行交互 提供了初始化、发送消息和处理函数调用的功能
class OpenAIClient:
    # 初始化
    def __init__(self, api_key, base_url, model, system_prompt, tools=None):
        """
        Initializes the OpenAIClient with the given API key, base URL, model, and system prompt.
        :param api_key: The API key for authentication.
        :param base_url: The base URL for the OpenAI API.
        :param model: The model to be used for generating responses.
        :param system_prompt: The system prompt to be used for the model.
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools
        # 计算对话轮数
        self.conversation_count = 0
        # 初始化消息列表
        self.messages = [
            {
                "role": "system",
                "content": self.system_prompt
            }
        ]

    # 发送消息
    def send_messages(self, messages_get):
        """
        Sends messages to the OpenAI API and returns the response.
        :param messages: The messages to be sent to the API.
        :return: The response from the API.
        """
        
        # 计算对话轮数
        self.conversation_count += 1
        # 添加用户消息
        # messages_get是一个list，将list中的每个元素添加到messages中
        for i in messages_get:
            self.messages.append(i)
        # 调用API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            # tools=self.tools
        )
        # 返回响应
        self.messages.append(response.choices[0].message)
        return response.choices[0].message

# 提取message字符串中的信息，获取[Funcall]的相关内容并整理成tool_calls的格式
def message_format(message):

    tool_calls = []
    # 将字符串中取出一行，若该行中含有[Function Call]，则提取函数名称和参数
    message_split = message.split("\n")
    for i in message_split:
        if "[Funcall]" in i:
            # 提取函数名称  [Funcall]:map_create();
            funcName = i.split(":")[1].split("(")[0].strip()
            # 提取参数 考虑到没有参数的情况 [Funcall]:map_create();[Funcall]: get_location(location:厨房);
            if "(" in i:
                funcArguments_str = i.split("(")[1].split(")")[0].strip()
            else:
                funcArguments_str = ""

            # 如果有参数 将参数字符串转换为字典
            if funcArguments_str != "":
                # 将参数字符串转换为字典
                funcArguments = {}
                for arg in funcArguments_str.split(";"):
                    key, value = arg.split(":")
                    key = key.strip()
                    value = value.strip()
                    # 去掉参数值的引号
                    value = value.replace("'", "").replace('"', '')
                    # 将参数添加到字典中
                    funcArguments[key] = value
            else:
                funcArguments = {}

            # 将函数名称和参数添加到tool_calls中
            tool_calls.append({
                "type": "function",
                "function": {
                    "name": funcName,
                    "arguments": funcArguments
                }
            })
    return tool_calls

# 对message.content一行一行检测，看段落中是否有[Function Call]，如果有则返回True，否则返回False
def judge_tool_call(message):
    message = message.content
    message_split = message.split("\n")
    for i in message_split:
        if "[Funcall]" in i:
            return True
    return False

# 初始化函数调用
def init_func_call():
    global system_prompt_cn
    global arm_control
    global car_control
    global vision_sensor
    global audio_sensor
    global map_sensor
    
    # 初始化类
    arm_control = ArmControl(

        arm_status=arm_get_status,
        arm_move=arm_move,
        arm_stop=arm_stop,
        arm_grab=arm_grab
    )
    car_control = CarControl(

        car_status=car_get_status,
        car_move=car_move,
        car_stop=car_stop
    )
    vision_sensor = VisionSensor(

        vision_image_get=image_capture,
        vision_object_find=object_find,
        vision_object_detection=object_detection
    )
    audio_sensor = AudioSensor(
        audio_capture=audio_capture,
        audio_speech_to_text=speech_to_text,
        audio_text_to_speech=text_to_speech
    )
    map_sensor = MapSensor(

        map_update=semantic_map_update,
        map_query_class=semantic_map_query,
        map_query_object=semantic_map_query,
        map_visualize=None
    )

    # 通过get_func_tools_info()方法获取工具信息并拼接到system_prompt_cn中
    system_prompt_cn += arm_control.get_func_tools_info()
    system_prompt_cn += car_control.get_func_tools_info()
    system_prompt_cn += vision_sensor.get_func_tools_info()
    system_prompt_cn += audio_sensor.get_func_tools_info()
    system_prompt_cn += map_sensor.get_func_tools_info()

# func_call函数 用于处理大模型生成的调用函数
def func_call(tool_calls):
    content_append = "调用函数返回结果如下"
    for tool_call in tool_calls:
        # print(f"Tool call: {tool_call}")
        if tool_call["type"] == "function":  
            function = tool_call["function"] 
            funcName = function["name"]  
            funcArguments = function["arguments"] 
            
            # print(f"Function name: {funcName}")
            # print(f"Function arguments: {funcArguments}")
            
            # 调用语音函数,播放当前函数名称
            audio_sensor.text_to_speech(f"调用函数名称为:{funcName}")
            
            content = ""
            
            # 将funcName funcArguments添加到message.txt中
            with open("message.txt", "a") as f:
                f.write("\n" + funcName + ":")
                f.write(str(funcArguments) + "\n")
            
            # 根据函数名称前一个下划线确定调用类调用相应的函数如果函数名包含"arm"，则调用机械臂控制类的函数
            if "arm" in funcName:
                content = arm_control.func_call(funcName, funcArguments)
            elif "car" in funcName:
                content = car_control.func_call(funcName, funcArguments)
            elif "vision" in funcName:
                content = vision_sensor.func_call(funcName, funcArguments)
            elif "audio" in funcName:
                content = audio_sensor.func_call(funcName, funcArguments)
            elif "map" in funcName:
                content = map_sensor.func_call(funcName, funcArguments)
            else:
                print(f"Function {funcName} not recognized.")
                continue
            

        # 输出函数调用的结果长度如果不为0
        if content != None:
            # 打印函数调用的结果
            # print(f"debug Funcall result: {content}")
            
            content_append = content_append + ";" + content
            
            # 播放函数调用的结果
            audio_sensor.text_to_speech(content)
            # 将content添加到messages.txt中
            with open("message.txt", "a") as f:
                f.write("\n" + content + "\n")
                
    # 如果分条加入的话则下次调用只针对最晚的content
    # 将第一个;替换成:
    content_append = content_append.replace(";", ":", 1)
    return [{"role": "user", "content": content_append}]  

def main():
    # 初始化函数调用
    init_func_call()
    
    api_key = "ollama"
    base_url = "http://162.105.175.7:11434/v1"
    model="deepseek-r1:14b"
    
    questions0 = "去厨房拿一个红色的杯子"
    questions1 = "去厨房拿一个红色的杯子"
    questions2 = "请你简单介绍下你自己"
    questions3 = "请你对当前楼层进行建图，每次都查询语义地图找到地图边界，走到边界后扫描,最后回到原点"
    questions4 = "帮我找到303房间，在建立好的地图上，检索水杯，得到坐标点，然后返回"
    questions5 = "前进一米"
    
    # 开始计时
    start_time = time.time()
    
    # 初始化OpenAIClient
    client = OpenAIClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        system_prompt=system_prompt_cn,
        tools=None
    )

    
    print("初始化完成，开始执行用户指令")
    
    message = client.send_messages([{"role": "user", "content": questions0}])
    
    
    
    # 将message的内容保存到文件中
    with open("message.txt", "a") as f:
        f.write(message.content)
        
    # message删去<think> ... </think>的内容

    while judge_tool_call(message) == True:
        # 提取message的content中的'{}'中的内容
        message = message.content
        message = message[message.find("{"):message.rfind("}") + 1]
        
        # tool_call是一个字典
        tool_calls = message_format(message)

        # 进行函数调用
        messages = func_call(tool_calls)
              
        # 发送消息
        message = client.send_messages(messages)

    print(message.content)
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")


    
if __name__ == "__main__":
    main()