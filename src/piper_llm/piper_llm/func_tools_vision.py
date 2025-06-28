# -*- coding: utf-8 -*-

'''
├─ 视觉感知类
│ ├─ 相机开启
│ ├─ 图像获取
│ ├─ 图像中物体检测
│ └─ 目标检测与定位
'''
class VisionSensor():
    def __init__(self, vision_image_get, vision_object_find, vision_object_detection):
        super().__init__()
        self.vision_image_get = vision_image_get
        self.vision_object_find = vision_object_find
        self.vision_object_detection = vision_object_detection
        
        self.current_image = None

        self.tools_info = """
            - vision_image_get() # 功能描述: 图像获取 参数描述: 无
            - vision_object_find(object: str) # 功能描述: 找到物体 参数描述: 物体名称(字符串形式)
            - vision_object_detection() # 功能描述: 物体标记 参数描述: 无
        """
        self.func_tools_list = [
            {# 图像获取
                "type": "function",
                "function": {
                    "name": "image_get",
                    "description": "Get image data",
                }
            },
            {# 图像中找到物体
                "type": "function",
                "function": {
                    "name": "find_object",
                    "description": "Find an object in the image",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The object to find",
                            }
                        },
                        "required": ["object"]
                    },
                }
            },
            {# 物体标记
                "type": "function",
                "function": {
                    "name": "object_detection",
                    "description": "Find an object in the image",
                }
            }
        ]
    # 获取VisionSensor类的tools信息 提供给function_call使用
    def get_func_tools_info(self):
        return self.tools_info
    def get_func_tools_list(self):
        return self.func_tools_list
    
    # 调用func_call函数来执行相应的功能
    def func_call(self, func_name, arguments):

        if func_name == "vision_image_get":
            return self.image_get()
        elif func_name == "vision_object_find":
            return self.find_object(arguments["object"])
        elif func_name == "vision_object_detection":
            return self.detect_object()
        else:
            raise ValueError(f"Function {func_name} not recognized.")
    
    # 调试接口

    def image_get(self):
        return self.vision_image_get()
    def find_object(self, object_name, image_data=None):
        return self.vision_object_find(object_name, image_data)
    def detect_object(self):
        return self.vision_object_detection()


'''
├─ 视觉感知类

│ ├─ 图像获取
│ ├─ 图像中物体检测
│ └─ 目标检测与定位
'''

# 函数名称:image_capture()
# 函数描述:图像获取
# 输入:none
# 输出:str(图片数据的位置)
def image_capture():
    print("Image captured")
    return "Image captured at ..."
# 函数名称:object_find()
# 函数描述:图像中物体检测
# 输入:str(要查找的物体名称), option:str(图片数据存储的位置)
# 输出:str(物体位置信息-标签/坐标)
# eg1:"杯子 在 x,y,z"
# eg1:"杯子 在 标签1处", 标签1需要对应一个坐标能够使其他函数能够获取使用
def object_find(target, image=None):
    print(f"Target location for {target} in {image}")
    return f"{target} located at x, y, z"
# 函数名称:object_detection()
# 函数描述:将图像中的物体进行标记-加入到语义地图?
# 输入:option:str(图片数据的位置)
# 输出:str(当前场景中的物体)
def object_detection(image=None):
    print(f"Object detection on {image}")
    return "Object detected"

