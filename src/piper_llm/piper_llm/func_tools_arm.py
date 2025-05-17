'''
├─ 机械臂控制类 
│ ├─ 获取机械臂状态
│ ├─ 机械臂移动
│ ├─ 机械臂急停
│ └─ 机械臂抓取物体
'''
class ArmControl():
    def __init__(self, arm_status, arm_move, arm_stop, arm_grab):
        super().__init__()
        self.arm_status = arm_status
        self.arm_move = arm_move
        self.arm_stop = arm_stop
        self.arm_grab = arm_grab
        '''
        tools_info:一个string,用于描述该类的功能
        该string会被传递给function_call的function参数中的description字段
        '''
        self.tools_info = """
            - arm_move(location: str) # 功能描述: 移动到指定位置 参数描述: 位置(字符串形式)
            - arm_grab(object: str) # 功能描述: 抓取物体 参数描述: 物体名称(字符串形式)
        """
        self.func_tools_list = [
            {# 机械臂移动
                "type": "function",
                "function": {
                    "name": "arm_move",
                    "description": "arm move a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The location the arm to go to",
                            }
                        },
                        "required": ["location"]
                    },
                }
            },
            {# 抓取物体
                "type": "function",
                "function": {
                    "name": "arm_grab",
                    "description": "Grab an object",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The object to grab",
                            }
                        },
                        "required": ["object"]
                    },
                }
            },
        ]
    # 获取FuncToolsArm类的tools信息 提供给function_call使用
    def get_func_tools_info(self):
        return self.tools_info
    def get_func_tools_list(self):
        return self.func_tools_list
    
    # 调用func_call函数来执行相应的功能
    def func_call(self, func_name, arguments):

        if func_name == "arm_status":
            return self.arm_status()
        elif func_name == "arm_move":
            return self.arm_move(arguments["location"])
        elif func_name == "arm_grab":
            return self.arm_grab(arguments["object"])
        else:
            raise ValueError(f"Function {func_name} not recognized.")
        
    # 调试接口

    def status(self):
        return self.arm_status()
    def move_to(self, location):
        return self.arm_move(location)
    def grab(self, object_name):
        return self.arm_grab(object_name)
    
    

'''
├─ 机械臂控制类函数
│ ├─ 获取机械臂状态
│ ├─ 机械臂移动
│ ├─ 机械臂急停
│ └─ 机械臂抓取物体
'''

# 函数名称:arm_get_status()
# 函数描述:获取机械臂状态
# 输入:none
# 输出:str(机械臂当前的状态)
def arm_get_status():
    print("Robot arm status: OK")
    return "Robot arm status: OK"
# 函数名称:arm_move()
# 函数描述:机械臂移动到指定位置
# 输入:str(位置信息-标签/坐标)
# 输出:str(机械臂最后的状态,位置信息-标签/坐标)
def arm_move(location):
    print(f"Robot arm moving to {location}")
    return f"Robot arm at {location} now"
# 函数名称:arm_stop()
# 函数描述:机械臂急停
# 输入:none
# 输出:none
def arm_stop():
    print("Robot arm emergency stop activated")
    return "Robot arm emergency stop activated"
# 函数名称:arm_grab()
# 函数描述:机械臂抓取物体
# 输入:str(物体名称)
# 正常输出:str(机械臂抓取的物体名称)
# 异常输出:str(机械臂无法抓取的错误信息-物体不存在/物体不在抓取范围内)
def arm_grab(object):
    print(f"Robot arm grabbing {object}")
    return f"Robot arm grabbed {object}"