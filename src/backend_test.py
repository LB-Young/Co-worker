import requests
import json
from sseclient import SSEClient

user_input = "我在中国上海出差，请查询今天的天气后，然后写一首与今天天气有关的诗要有诗名，并评论一下这首诗写的好不好。"
# user_input = "首先查询一下上海的天气，然后再查询一下华盛顿的天气。"
# user_input = "写一首与晴天有关的诗要有诗名，并评论一下这首诗写的好不好。"
buffer = ""
finished_flag = False
full_response = ""
headers = {
    "Accept": "text/event-stream",
    "Content-Type": "application/json"
}
response = requests.post(
    "http://localhost:8000/chat",
    json={"query": user_input},
    stream=True,
    headers=headers
)
client = SSEClient(response)
# 流式处理响应
try:
    for event in client.events():
        if event.data == "[DONE]":
            break
        data = event.data.replace("\\n","\n")
        print(f"收到消息: {data}")
except Exception as e:
    print(f"Error: {str(e)}")
finally:
    response.close()

"""
with requests.post(
    "http://localhost:8000/chat",
    json={"query": user_input},
    stream=True,s
    headers={'Accept': 'text/event-stream'}
) as response:
    
    # 流式处理响应
    buffer = ""
    full_response = ""
    for chunk in response.iter_content(chunk_size=1024):
        data = chunk.decode().strip()
        if data.startswith("data: "):
            data = json.loads(data[6:])['content']
            full_response += data
            print(full_response)
"""

"""
import aiohttp
import asyncio

async def main():

    full_response = ""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/chat",
            json={"query": user_input},
            headers={'Accept': 'text/event-stream'}
        ) as response:
            async for chunk in response.content.iter_any():
                data = chunk.decode().strip()
                if data.startswith("data: "):
                    data = json.loads(data[6:])['content']
                    full_response +=data
                    print(full_response)

asyncio.run(main())
"""