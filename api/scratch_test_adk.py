import asyncio
from typing import Mapping, Callable, Any, Sequence

from fastapi.responses import StreamingResponse
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from dotenv import load_dotenv
load_dotenv(".env", override=True)

def test_tool(query: str) -> dict:
    return {"status": "success", "result": f"Answer for {query}"}

async def test_adk():
    from google.genai import types as genai_types
    from google.adk.tools import FunctionTool
    
    agent = Agent(name="test_agent", model="gemini-2.5-flash", tools=[test_tool])
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name="app", user_id="test", session_id="test1")
    runner = Runner(agent=agent, app_name="app", session_service=session_service)

    print("Running...")
    async for event in runner.run_async(user_id="test", session_id="test1", new_message=genai_types.Content(role="user", parts=[genai_types.Part.from_text(text="Use tool to query 'hello'.")])):
        print("Got EVENT from:", event.author)
        for p in (event.content.parts if event.content else []):
            if p.text: print("  TEXT:", p.text)
            if p.function_call: print("  CALL:", p.function_call.name, p.function_call.args)
            if p.function_response: print("  RESP:", p.function_response.name, p.function_response.response)

if __name__ == "__main__":
    asyncio.run(test_adk())
