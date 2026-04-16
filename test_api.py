import asyncio
from backend.ai.router import call_gemini

async def test():
    result = await call_gemini(
        prompt='Return a JSON object with keys status and model, values ok and working respectively.',
        response_mime_type='application/json'
    )
    print(f'API works! Result: {result}')

asyncio.run(test())
