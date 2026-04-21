import json
import uuid
import traceback
from typing import List, AsyncGenerator

from google.adk.events import Event
from google.genai import types as genai_types
from google.adk.sessions import Session
from google.adk.runners import Runner

from .prompt import ClientMessage

def seed_adk_session(session: Session, messages: List[ClientMessage]) -> genai_types.Content:
    """
    Populate an ADK session with historical messages and return the final user message.
    """
    for message in messages[:-1]:
        parts = []
        if message.parts:
            for part in message.parts:
                if part.type == 'text':
                    parts.append(genai_types.Part.from_text(text=part.text or ''))
                elif part.type.startswith('tool-'):
                    if part.state == 'output-available' and part.output is not None:
                        parts.append(genai_types.Part.from_function_response(
                            name=part.toolName,
                            response=part.output
                        ))
                    else:
                        tool_call_args = part.input if part.input is not None else part.args
                        parts.append(genai_types.Part.from_function_call(
                            name=part.toolName,
                            args=tool_call_args if isinstance(tool_call_args, dict) else json.loads(tool_call_args)
                        ))
        elif message.content:
            parts.append(genai_types.Part.from_text(text=message.content))
            
        if message.toolInvocations:
            for inv in message.toolInvocations:
                parts.append(genai_types.Part.from_function_response(
                    name=inv.toolName,
                    response=inv.result
                ))
        
        if not parts:
            continue
                
        content = genai_types.Content(role="user" if message.role == "user" else "model", parts=parts)
        author = "user" if message.role == "user" else "chat_agent" 
        session.events.append(Event(author=author, content=content))
        
    last_msg = messages[-1]
    last_parts = []
    if last_msg.parts:
        for part in last_msg.parts:
            if part.type == 'text':
                 last_parts.append(genai_types.Part.from_text(text=part.text or ''))
    elif last_msg.content:
        last_parts.append(genai_types.Part.from_text(text=last_msg.content))
        
    if not last_parts:
        last_parts.append(genai_types.Part.from_text(text=""))
        
    return genai_types.Content(role="user", parts=last_parts)

async def stream_adk_runner(
    runner: Runner,
    user_id: str,
    session_id: str,
    new_message: genai_types.Content
) -> AsyncGenerator[str, None]:
    try:
        def format_sse(payload: dict) -> str:
            return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"

        message_id = f"msg-{uuid.uuid4().hex}"
        text_stream_id = "text-1"
        text_started = False
        text_finished = False

        yield format_sse({"type": "start", "messageId": message_id})
        
        # Track pending tool calls to map response back to call ID
        pending_tool_calls = {}

        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=new_message):
            if event.author == "user":
                continue
                
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        if not text_started:
                            yield format_sse({"type": "text-start", "id": text_stream_id})
                            text_started = True
                        yield format_sse({"type": "text-delta", "id": text_stream_id, "delta": part.text})
                    
                    if part.function_call:
                        call_id = f"call-{uuid.uuid4().hex}"
                        pending_tool_calls[part.function_call.name] = call_id
                        yield format_sse({
                            "type": "tool-input-start",
                            "toolCallId": call_id,
                            "toolName": part.function_call.name,
                        })
                        yield format_sse({
                            "type": "tool-input-available",
                            "toolCallId": call_id,
                            "toolName": part.function_call.name,
                            "input": part.function_call.args if isinstance(part.function_call.args, dict) else {},
                        })

                    if part.function_response:
                        call_id = pending_tool_calls.get(part.function_response.name, f"call-{uuid.uuid4().hex}")
                        yield format_sse({
                            "type": "tool-output-available",
                            "toolCallId": call_id,
                            "output": part.function_response.response, # Assuming dict
                        })

        if text_started and not text_finished:
            yield format_sse({"type": "text-end", "id": text_stream_id})
            text_finished = True

        yield format_sse({"type": "finish"})
        yield "data: [DONE]\n\n"
    except Exception:
        traceback.print_exc()
        raise
