

'''
├─ 基座小车控制类 
│ ├─ 小车使能
│ ├─ 获取小车状态
│ ├─ 小车移动
│ ├─ 小车急停
'''
class CarControl():
    def __init__(self, car_status, car_move, car_stop):
        super().__init__()
        self.car_status = car_status
        self.car_move = car_move
        self.car_stop = car_stop
        '''
        tools_info:一个string,用于描述该类的功能
        该string会被传递给function_call的function参数中的description字段
        '''
        self.tools_info = """
            - car_stop() # 功能描述: 停止小车 参数描述: 无
            - car_move(location: str) # 功能描述: 移动到指定位置 参数描述: 位置(字符串形式)
        """
        self.func_tools_list = [
            {# 小车移动
                "type": "function",
                "function": {
                    "name": "car_move",
                    "description": "car move a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The location the car to go to",
                            }
                        },
                        "required": ["location"]
                    },
                }
            },
            {# 小车急停
                "type": "function",
                "function": {
                    "name": "car_stop",
                    "description": "Stop the car",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        # 无参数
                        # 直接调用函数
                    },
                }
            },
        ]
    # 获取FuncToolsCar类的tools信息 提供给function_call使用
    def get_func_tools_info(self):
        return self.tools_info
    def get_func_tools_list(self):
        return self.func_tools_list
    
    # 调用func_call函数来执行相应的功能
    def func_call(self, func_name, arguments):

        if func_name == "car_status":
            return self.car_status()
        elif func_name == "car_move":
            return self.car_move(arguments["location"])
        elif func_name == "car_stop":
            return self.car_stop()
        else:
            raise ValueError(f"Function {func_name} not recognized.")
        
    # 调试接口
    def status(self):
        return self.car_status()
    def move_to(self, location):
        return self.car_move(location)
    def stop(self):
        return self.car_stop()
    



'''
├─ 基座小车控制类 
│ ├─ 获取小车状态
│ ├─ 小车移动
│ ├─ 小车急停
'''

# 函数名称:car_get_status()
# 函数描述:获取小车状态
# 输入:none
# 输出:str(小车当前的状态,位置信息-标签/坐标)
# eg1:"小车 在 x,y,z"
# eg1:"小车 在 起点位置", 起点位置需要对应一个坐标能够使其他函数能够获取使用
def car_get_status():
    print("Car status: OK")
    return "Car status: OK"
# 函数名称:car_move()
# 函数描述:小车移动到指定位置
# 输入:str(位置信息-标签/坐标)
# 输出:str(小车最后的状态,位置信息-标签/坐标)
def car_move(location):
    print(f"Car moving to {location}")
    return f"Car at {location} now"
# 函数名称:car_stop()
# 函数描述:小车急停
# 输入:none
# 输出:none
def car_stop():
    print("Car emergency stop activated")
    return "Car emergency stop activated"   
