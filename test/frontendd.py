import requests
import json
from sseclient import SSEClient

def chat_stream():
    url = "http://localhost:9000/chat"
    headers = {
        "Accept": "text/event-stream",
        "Content-Type": "application/json"
    }
    data = {
        "query": "测试问题"
    }
    
    response = requests.post(url, json=data, headers=headers, stream=True)
    client = SSEClient(response)
    
    try:
        for event in client.events():
            if event.data == "[DONE]":
                break
            print(f"收到消息: {event.data}")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        response.close()

if __name__ == "__main__":
    chat_stream()