


'''
├─ 雷达感知(TODO)
│ ├─ 雷达状态检测
...
'''

class RadarSensor():
    def __init__(self, radar_status):
        super().__init__()
        self.radar_status = radar_status
        '''
        tools_info:一个string,用于描述该类的功能
        该string会被传递给function_call的function参数中的description字段
        '''
        self.tools_info = """
            - radar_status()
        """
        self.func_tools_list = [
            {# 雷达状态检测
                "type": "function",
                "function": {
                    "name": "radar_status",
                    "description": "check the radar",
                }
            },
        ]
        
    def get_func_tools_info(self):
        return self.tools_info
    def get_func_tools_list(self):
        return self.func_tools_list
    
    