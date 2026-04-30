import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"

async def stream_llm(messages):
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            OLLAMA_URL,
            json={
                "model": "llama3",
                "messages": [m.dict() for m in messages],
                "stream": True,
            },
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    yield line
