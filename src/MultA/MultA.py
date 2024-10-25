import json
from openai import OpenAI
from .types import Agent


class MultA:
    def __init__(self, model=None, client=None):
        if client is not None:
            self.client = client
        else:
            self.client = OpenAI()
        if model is None:
            self.model = "gpt-3.5-turbo"
        else:
            self.model = model
        self.tools = []
        self.agent_function_mapping = {}

    async def init_tools(self, agents=None, tools=None):
        if agents is not None:
            for agent in agents:
                self.agent_function_mapping[agent.name] = {"type":"agent",
                                                           "object":agent}
                cur_tool = {
                    "type": "function",
                    "function": {
                        "name": agent.name,
                        "description": agent.description,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "prompt":{
                                    "type": "string",
                                    "description": "需要由该代理执行的任务描述。"
                                }
                            },
                            "required": ["prompt"]
                        }
                    }
                }
                self.tools.append(cur_tool)
        if tools is not None:
            for tool in tools:
                tool_name = tool.__name__.split(".")[-1]
                self.agent_function_mapping[tool_name] = {"type":"function",
                                                           "object":tool}
                tool_format = tool(get_tool_format=True)
                self.tools.append(tool_format)

    async def run(self, query, agents=None, tools=None):
        await self.init_tools(agents, tools)
        messages = [{
            "role": "system",
            "content":"""你们是一位专业的人工智能助手团队，会一步一步解释你们的推理。每个步骤会由一个人来做出回复，对于一个步骤需要提供一个标题来描述你们在该步骤中所做的事情以及内容。决定是否需要调用其他人帮忙采取其他步骤，或者是否准备好给出最终答案。使用“title”、“content”和“query”（“continue”或“finished”）键以 JSON 格式进行响应，其中title是描述content的主要内容。尽可能多地使用推理步骤。至少 3. 了解您作为LLM的局限性以及您能做什么和不能做什么。在你的推理中，包括对替代答案的探索。考虑一下之前的人回复的答案可能是错的，如果他们的推理是错误的，那么它会错在哪里。充分测试所有其他可能性。当之前的人回复的答案错了的时候，你需要解释他们错在哪里并开始使用另一种方法重新分步执行，不要只是说您正在重新解答。
            
            合法json回答的样例:
            {
                "title": "步骤1",
                "content": "这是步骤1的内容",
                "query_state": "continue"
            }
            """},
            {"role": "user", "content": query},
            {"role": "assistant", "content": "谢谢你！我们现在将按照指示一步步思考，从头开始分解问题,并分步协作回答。"
            }
            ]
        if agents is None:
            result = self.client.chat.completions.create(messages=messages)
            return result.choices[0].message.content
        else:
            next_agent = None
            next_agent_name, next_agent_params, title, query_state = await self.choose_next_agent(messages)
            next_agent = self.agent_function_mapping[next_agent_name]['object']
            next_type = self.agent_function_mapping[next_agent_name]['type']
            times = 0
            
            while times < 5 and next_agent is not None:
                # print("title:", title)
                if next_type == "agent":
                    cur_result, next_agent_name, next_agent_params, title, query_state = await next_agent.run(prompt=next_agent_params['prompt'], messages=messages, tools=self.tools)
                    if next_agent_name is None:
                        break
                    next_agent = self.agent_function_mapping[next_agent_name]['object']
                    next_type = self.agent_function_mapping[next_agent_name]['type']
                    messages.append({"role": "assistant", "content": cur_result})
                    print(cur_result)
                    times += 1
                    if query_state == "finished":
                        break
                else:
                    tool_result = next_agent(**next_agent_params)
                    cur_message = {"role": "user", "content": f"assistant调用的tool {next_agent_name} 的返回结果为 {tool_result}。请将这个结果重新组织一下表述，与上下文能够连贯。"}
                    response = self.client.chat.completions.create(
                                                                    tools=self.tools,
                                                                    model=self.model,
                                                                    messages=messages + [cur_message]  
                                                                )
                    response = json.loads(response.choices[0].message.content.replace("```json\n", "").replace("\n```",""))
                    cur_result = response['content']
                    messages.append({"role": "assistant", "content": cur_result})
                    print(cur_result)
                    times += 1
                    if query_state == "finished":
                        break

                    next_agent_name, next_agent_params, title, query_state = await self.choose_next_agent(messages)
                    next_agent = self.agent_function_mapping[next_agent_name]['object']
                    next_type = self.agent_function_mapping[next_agent_name]['type']

    async def choose_next_agent(self, messages):
        if len(messages) > 3:
            cur_message = {"role": "user", "content": "请接着上一个回答的的内容，继续分析下一个小步骤应该干什么。"}
            response = self.client.chat.completions.create(
                tools=self.tools,
                model=self.model,
                messages=messages + [cur_message],
            )
        else:
            response = self.client.chat.completions.create(
                tools=self.tools,
                model=self.model,
                messages=messages,
            )
        time = 0
        while time <= 3 and response.choices[0].message.tool_calls is None:
            response = json.loads(response.choices[0].message.content.replace("```json\n", "").replace("\n```",""))
            title = response['title']
            next_agent_content = response['content']
            query_state = response['query_state']
            response = self.client.chat.completions.create(
                tools=self.tools,
                model=self.model,
                messages=messages[3:]+[{"role": "user", "content": next_agent_content}],
                tool_choice = "required"
            )
            time += 1
        next_agent_name = response.choices[0].message.tool_calls[0].function.name
        next_agent_params = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
        return next_agent_name, next_agent_params, title, query_state
    