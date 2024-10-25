import json


class Agent:
    def __init__(self, name, client, model, description, functions):
        self.name = name
        self.client = client
        self.model = model
        self.description = description
        self.functions = functions

    async def run(self, prompt, messages, tools):
        cur_message = {'role': 'user', 'content': f"经过团队分析，当前步骤为：“{prompt}”应该由你来解答，请按照要求的json结构给出你对这个步骤的回答，请保持与上文的连贯性。"}
        cur_response = self.client.chat.completions.create(
            model=self.model,
            messages=messages + [cur_message],
        )
        response = json.loads(cur_response.choices[0].message.content.replace("```json\n", "").replace("\n```",""))
        title = response['title']
        cur_result = response['content']
        query_state = response['query_state']

        if query_state == "finished":
            next_agent_name = None
            next_agent_params = None
        else:
            next_agent_name, next_agent_params, title, query_state = await self.get_next_Agent(messages, tools, cur_result)

        return cur_result, next_agent_name, next_agent_params, title, query_state

    async def get_next_Agent(self, messages, tools, cur_result):
        if len(messages) > 3:
            cur_message = {"role": "user", "content": "请接着上一个回答的的内容，继续分析下一个小步骤应该干什么。"}
            response = self.client.chat.completions.create(
                tools=tools,
                model=self.model,
                messages=messages + [{"role": "assistant", "content": cur_result}] + [cur_message],
            )
        else:
            response = self.client.chat.completions.create(
                tools=tools,
                model=self.model,
                messages=messages + [{"role": "assistant", "content": cur_result}],
            )
        time = 0
        while time <= 3 and response.choices[0].message.tool_calls is None:
            response = json.loads(response.choices[0].message.content.replace("```json\n", "").replace("\n```",""))
            title = response['title']
            next_agent_content = response['content']
            query_state = response['query_state']
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