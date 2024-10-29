import requests
import json


user_input = "我在中国上海出差，请查询今天的天气后，然后写一首与今天天气有关的诗要有诗名，并评论一下这首诗写的好不好。"
buffer = ""
finished_flag = False
full_response = ""
with requests.post(
    "http://localhost:8000/chat",
    json={"query": user_input},
    stream=True,
    headers={'Accept': 'text/event-stream'}
) as response:
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            buffer += chunk.decode()
            while '\n\n' in buffer:
                line, buffer = buffer.split('\n\n', 1)
                if line.startswith('data: '):
                    if line.strip() == 'data: [DONE]':
                        finished_flag = True
                        break
                    try:
                        data = json.loads(line[6:])
                        if 'error' in data:
                            print("error1")
                            break
                        new_content = data.get('content', '')
                        if new_content == "done!":
                            break
                        full_response += new_content
                        print(full_response)
                    except json.JSONDecodeError:
                        continue
        if finished_flag:
            break

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