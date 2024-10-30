import asyncio
import aiohttp
import json
from typing import Optional, Dict, Any, List, Union, AsyncGenerator

class ToolCall:
    def __init__(self, data: Dict):
        self.id = data.get('id')
        self.type = data.get('type')
        self.function = self.Function(data.get('function', {}))

    class Function:
        def __init__(self, data: Dict):
            self.name = data.get('name')
            self.arguments = data.get('arguments')

        def to_dict(self) -> Dict:
            return {
                "name": self.name,
                "arguments": self.arguments
            }

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "function": self.function.to_dict()
        }

class FunctionCall:
    def __init__(self, data: Dict):
        self.name = data.get('name')
        self.arguments = data.get('arguments')

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "arguments": self.arguments
        }

class Message:
    def __init__(self, data: Dict):
        self.content = data.get('content')
        self.role = data.get('role')
        self.tool_calls = [ToolCall(tc) for tc in data.get('tool_calls', [])] if data.get('tool_calls') else None
        self.function_call = FunctionCall(data['function_call']) if data.get('function_call') else None
        self.tool_call_id = data.get('tool_call_id')
        self.name = data.get('name')

    def __str__(self):
        return self.content if self.content is not None else ""

    def to_dict(self) -> Dict:
        result = {"role": self.role}
        if self.content is not None:
            result["content"] = self.content
        if self.tool_calls:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.function_call:
            result["function_call"] = self.function_call.to_dict()
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.name:
            result["name"] = self.name
        return result

class Choice:
    def __init__(self, data: Dict):
        self.index = data.get('index')
        self.message = Message(data.get('message', {})) if data.get('message') else None
        self.delta = Message(data.get('delta', {})) if data.get('delta') else None
        self.finish_reason = data.get('finish_reason')
        self.logprobs = data.get('logprobs')

    def to_dict(self) -> Dict:
        result = {"index": self.index}
        if self.message:
            result["message"] = self.message.to_dict()
        if self.delta:
            result["delta"] = self.delta.to_dict()
        if self.finish_reason:
            result["finish_reason"] = self.finish_reason
        if self.logprobs:
            result["logprobs"] = self.logprobs
        return result

class Usage:
    def __init__(self, data: Dict):
        self.prompt_tokens = data.get('prompt_tokens')
        self.completion_tokens = data.get('completion_tokens')
        self.total_tokens = data.get('total_tokens')

    def to_dict(self) -> Dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens
        }

class ChatCompletionResponse:
    def __init__(self, data: Dict):
        self.id = data.get('id')
        self.object = data.get('object')
        self.created = data.get('created')
        self.model = data.get('model')
        self.system_fingerprint = data.get('system_fingerprint')
        self.choices = [Choice(choice) for choice in data.get('choices', [])]
        self.usage = Usage(data.get('usage', {})) if data.get('usage') else None
        self._cached_completion = None

    @property
    def completion(self) -> str:
        """便捷访问第一个选项的内容"""
        if self._cached_completion is None and self.choices:
            if self.choices[0].message:
                self._cached_completion = str(self.choices[0].message)
            elif self.choices[0].delta:
                self._cached_completion = str(self.choices[0].delta)
        return self._cached_completion or ''

    def to_dict(self) -> Dict:
        result = {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": [choice.to_dict() for choice in self.choices]
        }
        if self.system_fingerprint:
            result["system_fingerprint"] = self.system_fingerprint
        if self.usage:
            result["usage"] = self.usage.to_dict()
        return result

class ChatCompletion:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self._session = None

    async def create(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        stream: bool = False,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
        **kwargs
    ) -> Union[ChatCompletionResponse, AsyncGenerator[ChatCompletionResponse, None]]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        if tools:
            data["tools"] = tools
        if tool_choice:
            data["tool_choice"] = tool_choice

        if self._session is None:
            self._session = aiohttp.ClientSession()

        try:
            async with self._session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_data = await response.json()
                    raise Exception(f"API调用失败: {error_data}")

                if stream:
                    return self._handle_stream_response(response)
                else:
                    response_data = await response.json()
                    return ChatCompletionResponse(response_data)

        except Exception as e:
            raise Exception(f"请求失败: {str(e)}")

    async def _handle_stream_response(self, response):
        async for line in response.content:
            line = line.decode('utf-8').strip()
            if line:
                if line.startswith('data: '):
                    line = line[6:]
                if line == '[DONE]':
                    break
                try:
                    response_data = json.loads(line)
                    yield ChatCompletionResponse(response_data)
                except json.JSONDecodeError:
                    continue

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

class AsyncOpenAI:
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    async def _make_request(
        self,
        tools=None,
        model=None,
        messages=None,
        tool_choice=None
    ) -> Dict[str, Any]:
        data={}
        if tools is not None:
            data["tools"] = tools
        if model is not None:
            data["model"] = model
        if messages is not None:
            data["messages"] = messages
        if tool_choice is not None:
            data["tool_choice"] = tool_choice
        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(
                    method="POST",
                    url=f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=data
                ) as response:
                    response_data = await response.json()
                    if response.status != 200:
                        raise Exception(f"API调用失败: {response_data}")
                    response = ChatCompletionResponse(response_data)
                    return response
            except aiohttp.ClientError as e:
                raise Exception(f"网络请求错误: {str(e)}")

    async def chat_completion(
        self,
        tools=None,
        model=None,
        messages=None,
        tool_choice=None
    ) -> Dict[str, Any]:
        return await self._make_request(tools=tools, model=model, messages=messages, tool_choice=tool_choice)

# 使用示例
async def main():
    client = AsyncOpenAI("你的API密钥")
    
    # 创建多个并发请求
    messages = [
        {"role": "user", "content": "你好,请简单介绍下自己"}
    ]
    
    tasks = []
    for _ in range(3):  # 创建3个并发请求
        task = client.chat_completion(messages)
        tasks.append(task)
    
    try:
        # 等待所有请求完成
        responses = await asyncio.gather(*tasks)
        for i, response in enumerate(responses, 1):
            print(f"响应 {i}:", response['choices'][0]['message']['content'])
    except Exception as e:
        print(f"发生错误: {str(e)}")

# 运行异步代码
if __name__ == "__main__":
    asyncio.run(main())