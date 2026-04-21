import uuid
import os
from typing import List

from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request as FastAPIRequest
from fastapi.responses import StreamingResponse

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from .utils.prompt import ClientMessage
from .utils.stream import patch_response_with_headers
from .utils.tools import AVAILABLE_TOOLS
from .utils.adk_helpers import seed_adk_session, stream_adk_runner

from vercel import oidc
from vercel.headers import set_headers

load_dotenv(dotenv_path=".env", override=True)

app = FastAPI()

@app.middleware("http")
async def _vercel_set_headers(request: FastAPIRequest, call_next):
    set_headers(dict(request.headers))
    return await call_next(request)

class Request(BaseModel):
    messages: List[ClientMessage]

@app.post("/api/chat")
async def handle_chat_data(request: Request, protocol: str = Query('data')):
    messages = request.messages

    agent = Agent(
        name="chat_agent",
        model="gemini-2.5-flash",
        tools=list(AVAILABLE_TOOLS.values())
    )
    
    session_service = InMemorySessionService()
    session_id = f"sess-{uuid.uuid4().hex}"
    user_id = "default_user"
    
    session = await session_service.create_session(app_name="app", user_id=user_id, session_id=session_id)
    new_message = seed_adk_session(session, messages)
    
    runner = Runner(agent=agent, app_name="app", session_service=session_service)
    
    response = StreamingResponse(
        stream_adk_runner(runner, user_id, session_id, new_message),
        media_type="text/event-stream",
    )
    return patch_response_with_headers(response, protocol)
