import asyncio
from MultA.MultA import MultA
from MultA.types import Agent, Response
from openai import OpenAI
from MultA.async_llm import AsyncOpenAI
from MultA.tools.get_weather import get_weather

async def main():
    a = OpenAI(                        api_key="sk-bbbb062c55f24dd5928f4c4448c37f1f",
                        base_url="https://api.deepseek.com",)
    print(type(a))
    breakpoint()
    client = AsyncOpenAI(
                        api_key="sk-bbbb062c55f24dd5928f4c4448c37f1f",
                        base_url="https://api.deepseek.com",
                    )
    write_poetry = Agent("write_poetry", client, "deepseek-chat", "可以根据特定的主题写诗,包括四言绝句，八言律诗等", ["write_poetry"])
    poetry_review = Agent("poetry_review", client, "deepseek-chat", "你是一个古诗专家，可以评价古诗词，并给出详细的评价。", ["poetry_review"])
    query = "我在中国上海出差，请查询今天的天气后，然后写一首与今天天气有关的诗要有诗名，并评论一下这首诗写的好不好。"
    multa = MultA(model="deepseek-chat", client=client)
    response = multa._execute_plan(query=query, agents=[write_poetry, poetry_review], tools=[get_weather])
    async for item in response:
        print(item, end="")
        # pass
        
if __name__ == "__main__":
    asyncio.run(main())