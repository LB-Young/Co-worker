from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import asyncio
import json

app = FastAPI()

async def stream_generator(query: str):
    """模拟一个流式生成器函数"""
    # 这里替换成你的实际生成逻辑
    for i in range(5):
        await asyncio.sleep(1)  # 模拟延迟
        print("1111")
        chunk = f"这是第 {i+1} 条消息\n"
        # 注意这里的格式，必须是正确的 SSE 格式
        yield f"data: {chunk}\n\n"
    yield "data: [DONE]\n\n"

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        query = data.get("query", "")
        
        return StreamingResponse(
            stream_generator(query),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        return {"error": str(e)}
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)