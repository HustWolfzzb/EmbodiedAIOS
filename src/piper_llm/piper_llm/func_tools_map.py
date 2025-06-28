# -*- coding: utf-8 -*-

'''
map中的功能嵌入到FuncToolsVision类中?
├─ 语义地图感知

│ ├─ 语义地图更新
│ ├─ 语义地图查询
│ └─ 语义地图可视化
'''
class MapSensor():
    def __init__(self, map_update, map_query_class, map_query_object, map_visualize=None):
        super().__init__()
        self.map_update = map_update
        self.map_query_class = map_query_class
        self.map_query_object = map_query_object
        self.map_visualize = map_visualize
        

        # self.tools_info = """
        #     - map_create() # 功能描述: 创建语义地图 参数描述: 无
        #     - map_update(object: str, info: str) # 功能描述: 更新语义地图 参数描述: 无
        #     - map_query_class() # 功能描述: 查询语义地图 参数描述: 物体类别
        #     - map_query_object(object: str) # 功能描述: 查询语义地图 参数描述: 物体名称
        #     - map_visualize() # 功能描述: 可视化语义地图 参数描述: 无
        # """
        
        self.tools_info = """
            - map_query_class(class: str) # 功能描述: 查询语义地图；参数描述: 物体类别；返回类别的物体
            - map_query_object(object: str) # 功能描述: 查询语义地图；参数描述: 物体名称；返回物体位置
        """
        self.func_tools_list = [
            {# 语义地图查询 
                "type": "function",
                "function": {
                    "name": "query_class",
                    "description": "Query the semantic map",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "object_class": {
                                "type": "string",
                                "description": "The object class to query",
                            }
                        },
                        "required": ["object_class"]
                    },
                }
            },
            {# 语义地图查询
                "type": "function",
                "function": {
                    "name": "query_object",
                    "description": "Query the semantic map",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "object_name": {
                                "type": "string",
                                "description": "The object name to query",
                            }
                        },
                        "required": ["object_name"]
                    },
                }
            },
            
        ]
    
    # 获取MapSensor类的tools信息 提供给function_call使用
    def get_func_tools_info(self):
        return self.tools_info
    def get_func_tools_list(self):
        return self.func_tools_list
    
    # 调用func_call函数来执行相应的功能
    def func_call(self, func_name, arguments):

        if func_name == "map_update":
            return self.update_map()
        elif func_name == "map_query_class":
            return self.map_query_class(arguments["class"])
        elif func_name == "map_query_object":
            return self.map_query_object(arguments["object"])
        elif func_name == "map_visualize":
            return self.visualize_map()
        else:
            raise ValueError(f"Function {func_name} not recognized.")
        
    # 调试接口

    def update_map(self):
        return self.map_update()
    def query_class_map(self, class_name):
        return self.map_query_class(class_name)
    def query_object_map(self, object_name):
        return self.map_query_object(object_name)
    def visualize_map(self):
        return self.map_visualize()



'''
├─ 语义地图感知
│ ├─ 语义地图更新
│ ├─ 语义地图查询
'''

# 函数名称:semantic_map_update()
# 语义地图更新-图像感知时调用该函数更新语义地图?
# 参数待定
def semantic_map_update():
    print("Updating semantic map")
    return "Semantic map updated"
# 函数名称:semantic_map_query
# 函数描述:语义地图中查询物体/类别
# 输入:str(要查询的物体/类别)
# 输出:str(物体位置信息/类别的种类描述)
def semantic_map_query(object):
    print(f"Querying {object} semantic map")
    return f"{object} found at x, y, z"




