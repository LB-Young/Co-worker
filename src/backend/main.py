from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from MultA.MultA import MultA
from MultA.types import Agent
from MultA.tools.get_weather import get_weather
from openai import OpenAI
import json
import asyncio

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def stream_generator(query: str):
    client = OpenAI(
        api_key="sk-bbbb062c55f24dd5928f4c4448c37f1f",
        base_url="https://api.deepseek.com",
    )
    write_poetry = Agent("write_poetry", client, "deepseek-chat", "可以根据特定的主题写诗,包括四言绝句，八言律诗等", ["write_poetry"])
    poetry_review = Agent("poetry_review", client, "deepseek-chat", "你是一个古诗专家，可以评价古诗词，并给出详细的评价。", ["poetry_review"])
    multa = MultA(model="deepseek-chat", client=client)

    try:
        async for chunk in multa._execute_plan(query, agents=[write_poetry, poetry_review], tools=[get_weather]):
            if chunk:  # 确保chunk不为空
                yield f"data: {json.dumps({'content': chunk})}\n\n"
        # 发送结束信号
        yield "data: [DONE]\n\n"
    except Exception as e:
        print(f"Stream generation error: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    query = data.get("query", "")
    return StreamingResponse(
        stream_generator(query),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
