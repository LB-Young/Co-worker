import json
import openai
from openai import AsyncOpenAI
# from .async_llm import AsyncOpenAI


class Agent:
    def __init__(self, name, client, model, description, role, functions):
        if not isinstance(client, openai.OpenAI):
            self.client_flag = "async"
        else:
            self.client_flag = "no_async"
        self.name = name
        self.client = client
        self.model = model
        self.description = description
        self.role = role
        self.functions = functions

    async def run(self, prompt, messages, tools):
        title = ""
        cur_result = ""
        query_state = ""
        cur_message = {'role': 'user', 'content': f"{self.role}\n\n经过团队分析，当前步骤需要处理的内容：“" + f"{prompt}" + """”应该由你来解答。结果以json形式返回。如：      
            {
                "step_result": "这段内容的摘要是：……",
                "step_title": "对内容做摘要",
                "query_state": "continue/finished"
            }
        其中step_result为当前步骤处理后的结果，step_title为给当前步骤起的标题，query_state为当前查询处理的状态，finished表示当前步骤是解决用户任务的最后一个步骤，continue表示当前步骤执行完毕后还需要采取后续的步骤继续处理。"""}
        if self.client_flag == "async":
            cur_response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages + [cur_message],
            )
        else:
            cur_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages + [cur_message],
            )
        response = json.loads(cur_response.choices[0].message.content.replace("```json\n", "").replace("\n```",""))
        title = response['step_title']
        cur_result = response['step_result']
        query_state = response['query_state']

        if query_state == "finished":
            next_agent_name = None
            next_agent_params = None
        else:
            next_agent_name, next_agent_params, title, query_state = await self.get_next_Agent(messages, tools, title + ":" +cur_result)

        return cur_result, next_agent_name, next_agent_params, title, query_state

    async def get_next_Agent(self, messages, tools, cur_result):
        if cur_result is not None:
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
        3. 任务的title要简介明了，并且title的字符要有一半以上来自于用户query中的字符。
        4. 仅从用户query中拆分步骤，不要增加额外的分析步骤。如果你分析的步骤超出了用户query表达的内容，用户会给你差评，请仔细阅读用户的query之后决定下一步骤是什么。"""}
            if self.client_flag == "async":
                response = await self.client.chat.completions.create(
                    tools=tools,
                    model=self.model,
                    messages=messages + [{"role": "assistant", "content": cur_result}] + [cur_message],
                )
            else:
                response = self.client.chat.completions.create(
                    tools=tools,
                    model=self.model,
                    messages=messages + [{"role": "assistant", "content": cur_result}] + [cur_message],
                )
        else:
            if self.client_flag == "async":
                response = await self.client.chat.completions.create(
                    tools=tools,
                    model=self.model,
                    messages=messages,
                )
            else:
                response = self.client.chat.completions.create(
                    tools=tools,
                    model=self.model,
                    messages=messages,
                )
        time = 0
        while time <= 3 and response.choices[0].message.tool_calls is None:
            response = json.loads(response.choices[0].message.content.replace("```json\n", "").replace("\n```",""))
            title = response['step_title']
            next_agent_content = response['step_content']
            query_state = response['query_state']
            if self.client_flag == "async":
                response = await self.client.chat.completions.create(
                    tools=tools,
                    model=self.model,
                    messages=messages[3:] + [{"role": "assistant", "content": cur_result}] + [{"role": "user", "content": next_agent_content}],
                    tool_choice = "required"
                )
            else:
                response = self.client.chat.completions.create(
                    tools=tools,
                    model=self.model,
                    messages=messages[3:] + [{"role": "assistant", "content": cur_result}] + [{"role": "user", "content": next_agent_content}],
                    tool_choice = "required"
                )
            time += 1
        next_agent_name = response.choices[0].message.tool_calls[0].function.name
        next_agent_params = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
        return next_agent_name, next_agent_params, title, query_state
    

class Response:
    def __init__(self):
        self.all_response = ""
        self.response = ""

    async def set_response(self, response):
        self.response = response
        self.all_response += response + "\n"

    async def get_response(self):
        for char in self.response:
            yield char