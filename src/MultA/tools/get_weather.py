async def get_weather(location=None, get_tool_format=False):
    """
    This function returns the current weather in the city of Paris.
    """
    if get_tool_format:
        return {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "获取天气",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "城市名"
                                }
                            },
                            "required": ["location"]
                        },
                    }
                }
    return {"location": location, "temperature": 20, "description": "Sunny"}
