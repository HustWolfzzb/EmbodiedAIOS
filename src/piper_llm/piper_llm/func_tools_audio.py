
'''
├─ 听觉感知类
│ ├─ 音频采集
│ ├─ 语音转文本
│ └─ 文本转语音
'''
class AudioSensor():
    def __init__(self, audio_capture, audio_speech_to_text, audio_text_to_speech):
        super().__init__()
        self.audio_capture = audio_capture
        self.speech_to_text = audio_speech_to_text
        self.text_to_speech = audio_text_to_speech
        

        self.tools_info = """
            - audio_capture(time: int) # 功能描述: 音频采集 参数描述: 时间(整数形式)
            - audio_speech_to_text(at: str) # 功能描述: 语音转文本 参数描述: 音频位置(字符串形式)
            - audio_text_to_speech(text: str) # 功能描述: 文本转语音 参数描述: 文本数据(字符串形式)
        """
        self.func_tools_list = [
            {
                "type": "function",
                "function": {
                    "name": "audio_capture",
                    "description": "Capture audio",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_data": {
                                "type": "string",
                                "description": "The audio data to capture",
                            }
                        },
                        "required": ["audio_data"]
                    },
                }
            },
        ]

    # 获取AudioSensor类的tools信息 提供给function_call使用
    def get_func_tools_info(self):
        return self.tools_info
    def get_func_tools_list(self):
        return self.func_tools_list
    # 调用func_call函数来执行相应的功能
    def func_call(self, func_name, arguments):
        if func_name == "audio_capture":
            return self.capture_audio(arguments["time"])
        elif func_name == "audio_speech_to_text":
            return self.speech_to_text(arguments["audio_data"])
        elif func_name == "audio_text_to_speech":
            return self.text_to_speech(arguments["text"])
        else:
            raise ValueError(f"Function {func_name} not recognized.")

    # 调试接口
    def capture_audio(self, time):
        return self.audio_capture(time)
    def speech_to_text(self, audio_data):
        return self.audio_speech_to_text(audio_data)
    def text_to_speech(self, text):
        return self.audio_text_to_speech(text)




'''
├─ 听觉感知类
│ ├─ 音频采集
│ ├─ 语音转文本
│ └─ 文本转语音
'''
# 函数名称:audio_capture()
# 函数描述:音频采集
# 输入:int(采集时间)
# 输出:str(音频数据的位置)
def audio_capture(time=10):
    print("Audio captured")
    return f"Audio captured {time} at ..."

# 函数名称:speech_to_text()
# 函数描述:语音转文本
# 输入:str(音频数据的位置)
# 输出:str(文本数据)
def speech_to_text(audio):
    print(f"Converting {audio} to text")
    return "Text from audio"
# 函数名称:text_to_speech()
# 函数描述:文本转语音
# 输入:str(文本数据)
# 输出:none;扬音器播放语音
def text_to_speech(text):
    print(f"Converting {text} to speech")
    return "Speech from text"

