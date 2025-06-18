import os
from dashscope import MultiModalConversation

# 将xxx/eagle.png替换为你本地图像的绝对路径
local_path = "/\data.png"
image_path = f"file://{local_path}"
messages = [{"role": "system",
                "content": [{"text": "你是一名资深的英雄联盟赛事分析师"}]},
                {'role':'user',
                'content': [{'image': image_path},
                            {'text': '请根据这个图片上的数据，对场上十名选手的数据表现进行评分，满分十分，输出给出选手名字跟评分'}]}]
response = MultiModalConversation.call(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key="你自己的apikey，阿里的",
    model="qwen-vl-max",  # 此处以qwen-vl-max-latest为例，可按需更换模型名称。模型列表：https://help.aliyun.com/model-studio/getting-started/model
    messages=messages)
print(response.output.choices[0].message.content[0]['text'])
