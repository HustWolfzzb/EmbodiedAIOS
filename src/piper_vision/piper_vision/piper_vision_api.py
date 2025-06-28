import json
import os

def load_semantic_map(file_path):
    """
    加载语义地图JSON文件。

    Args:
        file_path (str): 语义地图JSON文件的路径。

    Returns:
        dict: 加载的语义地图数据，如果文件不存在或无效则返回空字典。
    """
    if not os.path.exists(file_path):
        print(f"Error: Semantic map file '{file_path}' not found.")
        return {}
    if os.path.getsize(file_path) == 0:
        print(f"Error: Semantic map file '{file_path}' is empty.")
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error: '{file_path}' is not a valid JSON file.")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred while loading '{file_path}': {e}")
        return {}
    
node = None
lang_map = {
        "人": "person",
        "人机": "person",
        "椅子": "chair",
        "桌子": "table",
        "门": "door",
        "汽车": "car",
        "树": "tree",
}
map_path = "/home/lgw/study/ros_all/EmbodiedAIOS/map/map.json"

def get_coordinate_by_name(name):
    semantic_map_data = load_semantic_map(map_path)
    if name in semantic_map_data:
        return semantic_map_data[name]
    for chinese_name, english_name in lang_map.items():
        if chinese_name == name:
            return semantic_map_data[english_name]
    print(f"Error: '{name}' not found in the semantic map.")
    return None

if __name__ == "__main__":
    print(get_coordinate_by_name("person"))