from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import json
from dotenv import load_dotenv
from agent import workflow
import uuid

load_dotenv()

app = FastAPI(title="Classroom Finder Agent")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class ChatResponse(BaseModel):
    message: str
    classrooms: Optional[List[Dict[str, Any]]] = None
    toolCalled: bool = False

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Chat endpoint that processes messages using LangChain agent.
    Expected to be called by the backend with proper authorization.
    """
    try:
        # Validate authorization header from backend
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required")
        
        # Generate unique thread ID for conversation
        thread_id = str(uuid.uuid4())
        
        # Convert messages to LangChain format
        messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in request.messages
        ]
        
        # Invoke agent workflow (async to support async tools)
        response = await workflow.ainvoke(
            {"messages": messages},
            config={"configurable": {"thread_id": thread_id}}
        )
        
        # Extract response
        if response and "messages" in response:
            last_message = response["messages"][-1]
            
            # Check if tool was called by inspecting message history
            tool_called = any(
                hasattr(msg, "tool_calls") and msg.tool_calls 
                for msg in response["messages"]
            )
            
            # Extract classroom data from ToolMessage artifacts
            # When tools use response_format="content_and_artifact", the artifact
            # is stored on the ToolMessage (not the final AIMessage).
            classrooms = None
            for msg in response["messages"]:
                if hasattr(msg, "artifact") and isinstance(msg.artifact, list) and len(msg.artifact) > 0:
                    # Only use classroom artifacts (dicts with 'id' and 'building' keys)
                    if isinstance(msg.artifact[0], dict) and "building" in msg.artifact[0]:
                        classrooms = msg.artifact
            
            return ChatResponse(
                message=last_message.content,
                classrooms=classrooms,
                toolCalled=tool_called
            )
        else:
            raise HTTPException(status_code=500, detail="No response from agent")
            
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Streaming chat endpoint using Server-Sent Events.
    Streams LLM tokens as they are generated, then emits a final done event with classrooms.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    thread_id = str(uuid.uuid4())
    messages = [
        {"role": msg.role, "content": msg.content}
        for msg in request.messages
    ]

    async def generate():
        full_response = ""
        classrooms = []
        try:
            async for event in workflow.astream_events(
                {"messages": messages},
                config={"configurable": {"thread_id": thread_id}},
                version="v2",
            ):
                kind = event.get("event")
                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        text = chunk.content
                        if isinstance(text, str) and text:
                            full_response += text
                            yield f"data: {json.dumps({'text': text})}\n\n"
                elif kind == "on_chain_end" and event.get("name") == "LangGraph":  # debug: print name if classrooms are empty
                    # Extract classrooms from the final graph output
                    output = event.get("data", {}).get("output", {})
                    final_messages = output.get("messages", [])
                    for msg in final_messages:
                        if hasattr(msg, "artifact") and msg.artifact:
                            classrooms = msg.artifact
                            break

        except GeneratorExit:
            return
        except Exception as e:
            print(f"Error during streaming: {e}")

        yield f"data: {json.dumps({'done': True, 'classrooms': classrooms})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
