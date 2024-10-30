import json
import asyncio
import openai
from openai import OpenAI, AsyncOpenAI
from .types import Agent
from typing import AsyncGenerator, List, Dict
# from .async_llm import AsyncOpenAI


class MultA:
    def __init__(self, api_key=None, base_url=None, model=None, client=None):
        if not isinstance(client, openai.OpenAI):
            self.client_flag = "async"
        else:
            self.client_flag = "no_async"
        if client is not None:
            self.client = client
        else:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
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
                tool_format = await tool(get_tool_format=True)
                self.tools.append(tool_format)

    async def run(self, query: str, agents=None, tools=None) -> AsyncGenerator[str, None]:
        await self.init_tools(agents=agents, tools=tools)
        messages = [{
            "role": "system",
            "content":"""你们是一位专业的人工智能助手团队，你们可以通过分工合作完美的解决问题，并且会一步一步解释你们的推理。你们会按照指示一步步思考，从头开始分解问题,并分步协作回答。拆解的每个单独的步骤会由一个人来做出回复，并且当前问题是否需要继续采取后续步骤由正在执行的人分析问题和已经完成的步骤来决定，而不是在一开始的时候就规划好所有步骤，而是走一步规划一步，后续的步骤可以对前面已经执行的步骤进行反驳和纠正下一步执行。
            """},
            {"role": "user", "content": query},
            {"role": "assistant", "content": "谢谢你！我们现在将按照指示一步步思考，从头开始分解问题,并分步协作回答。"
            }
            ]
        if agents is None:
            if self.client_flag == "async":
                result = await self.client.chat.completions.create(messages=messages)
            else:
                result = self.client.chat.completions.create(messages=messages)
                yield result.choices[0].message.content
        else:
            next_agent = None
            next_agent_name, next_agent_params, title, query_state = await self.choose_next_agent(messages)
            next_agent = self.agent_function_mapping[next_agent_name]['object']
            next_type = self.agent_function_mapping[next_agent_name]['type']
            times = 0
            past_title_set = set("")
            query_set = set(query)
            while times < 5 and next_agent is not None:
                title_set = set(title)
                print("past_title_set", past_title_set)
                print("query_set", query_set)
                print("title_set", title_set)
                print(len(title_set & past_title_set),  len(title_set & query_set), len(title_set))
                if len(title_set & past_title_set) / len(title_set) >= 0.8:
                    break
                if len(title_set & query_set) / len(title_set) <= 0.5:
                    break
                past_title_set = title_set
                yield f"#### step {times+1}: {title}({next_agent_name})\n\n"
                await asyncio.sleep(0.1)
                if next_type == "agent":
                    cur_result, next_agent_name, next_agent_params, title, query_state = await next_agent.run(
                        prompt=next_agent_params['prompt'], 
                        messages=messages, 
                        tools=self.tools
                    )
                    if len(cur_result) == 0:
                        break
                    messages.append({"role": "assistant", "content": title + ":" + cur_result})
                    print("cur_result:", cur_result)
                    yield cur_result.replace("\n", "\n\n").replace("\n\n\n\n", "\n\n") + "\n\n"
                    await asyncio.sleep(0.1)
                    
                    times += 1
                    if query_state == "finished":
                        break
                    next_agent = self.agent_function_mapping[next_agent_name]['object']
                    next_type = self.agent_function_mapping[next_agent_name]['type']
                else:
                    tool_result = await next_agent(**next_agent_params)
                    cur_message = {"role": "user", "content": f"assistant调用的tool {next_agent_name} 的返回结果为 {tool_result}。请将结果重新用自然语言组织表述，不要回复其它内容。"}
                    if self.client_flag == "async":
                        response = await self.client.chat.completions.create(
                            tools=self.tools,
                            model=self.model,
                            messages=messages + [cur_message]  
                        )
                    else:
                        response = self.client.chat.completions.create(
                            tools=self.tools,
                            model=self.model,
                            messages=messages + [cur_message]  
                        )   
                    cur_result = response.choices[0].message.content
                    messages.append({"role": "assistant", "content": title + ":" + cur_result})
                    print("cur_result:", cur_result)
                    yield cur_result.replace("\n", "\n\n").replace("\n\n\n\n", "\n\n") + "\n\n"
                    await asyncio.sleep(0.1)
                    
                    times += 1
                    if query_state == "finished":
                        break
                    next_agent_name, next_agent_params, title, query_state = await self.choose_next_agent(messages)
                    next_agent = self.agent_function_mapping[next_agent_name]['object']
                    next_type = self.agent_function_mapping[next_agent_name]['type']
            
            yield "done!"

    async def choose_next_agent(self, messages):
        cur_message = {"role": "user", "content": """如果你是当前任务的负责人，需要解决用户的问题，这个问题其它人已经处理了一些步骤，请在这些步骤的基础上确定下一步骤应该由谁来负责。结果以json形式返回。如：      
            {
                "step_content": "搜索与多模态大模型相关的论文",
                "step_title": "相关内容检索",
                "query_state": "continue/finished"
            }
        其中step_content为当前步骤需要处理的任务，step_title为给当前步骤起的标题，query_state为当前查询处理的状态，finished表示当前步骤是解决用户任务的最后一个步骤，continue表示当前步骤执行完毕后还需要采取后续的步骤继续处理。
        约束：
        1. 步骤切分要足够的小，这个小步骤仅由团队中的一个人或一个工具解决，不能是需要多人协作或者多个工具才能解决的步骤。如：“写一篇博客并发表到小红书”需要拆分成“写一篇博客”和“发表到小红书”两个步骤。 
        2. 每个步骤都需要来自用户的初始问题，不需要自行扩展。如：“写一篇博客并发表到小红书”可以拆分成“写一篇博客”和“发表到小红书”两个步骤，一定不要涉及用户query之外的步骤。
        3. 每个任务都是从用户query中解析得到，不能是捏造的任务。
        4. 注意LLM本身的幻觉，不要生成用户问题之外的步骤。"""}

        if self.client_flag == "async":
            response = await self.client.chat.completions.create(
                tools=self.tools,
                model=self.model,
                messages=messages + [cur_message],
            )
        else:
            response = self.client.chat.completions.create(
                tools=self.tools,
                model=self.model,
                messages=messages + [cur_message],
            )

        time = 0
        while time <= 3 and response.choices[0].message.tool_calls is None:
            response = json.loads(response.choices[0].message.content.replace("```json\n", "").replace("\n```",""))
            title = response['step_title']
            next_agent_content = response['step_content']
            query_state = response['query_state']

            if self.client_flag == "async":
                response = await self.client.chat.completions.create(
                    tools=self.tools,
                    model=self.model,
                    messages=messages[3:]+[{"role": "user", "content": next_agent_content}],
                    tool_choice = "required"
                )
            else:
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
    
    async def _execute_plan(self, query: str, agents=None, tools=None) -> AsyncGenerator[str, None]:
        async for item in self.run(query=query, agents=agents, tools=tools):
            if item != "done!":
                yield item
            else:
                yield item