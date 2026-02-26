from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, AsyncGenerator
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from agent import workflow
import uuid

load_dotenv()

def serialize_for_json(obj: Any) -> Any:
    """Recursively serialize objects for JSON, converting datetime to ISO strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    else:
        return obj

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
        import traceback
        traceback.print_exc()
        
        # Check if it's an API error (like 302 redirect or outage)
        error_str = str(e)
        if "302" in error_str or "outage" in error_str.lower() or "Moved Temporarily" in error_str:
            user_friendly_error = "The AI service is currently unavailable. Please try again later."
        elif "API" in error_str or "api" in error_str.lower():
            user_friendly_error = "There was an issue connecting to the AI service. Please try again."
        else:
            user_friendly_error = "An error occurred while processing your request. Please try again."
        
        raise HTTPException(status_code=503, detail=user_friendly_error)

@app.post("/chat/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Streaming chat endpoint that processes messages using LangChain agent.
    Returns Server-Sent Events (SSE) format.
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
        
        async def generate_stream() -> AsyncGenerator[str, None]:
            """Generator function that yields SSE-formatted chunks"""
            try:
                import asyncio
                classrooms = None
                
                # Get the agent's response (single invocation)
                response = await workflow.ainvoke(
                    {"messages": messages},
                    config={"configurable": {"thread_id": thread_id}}
                )
                
                if response and "messages" in response:
                    last_message = response["messages"][-1]
                    
                    # Extract classroom artifacts
                    for msg in response["messages"]:
                        if hasattr(msg, "artifact") and isinstance(msg.artifact, list) and len(msg.artifact) > 0:
                            if isinstance(msg.artifact[0], dict) and "building" in msg.artifact[0]:
                                classrooms = msg.artifact
                    
                    # Stream the response text in chunks for better UX
                    if hasattr(last_message, "content") and last_message.content:
                        full_text = str(last_message.content)
                        # Stream in word-sized chunks
                        words = full_text.split(' ')
                        for i, word in enumerate(words):
                            chunk = word + (' ' if i < len(words) - 1 else '')
                            yield f"data: {json.dumps({'text': chunk})}\n\n"
                            # Small delay to make streaming visible
                            await asyncio.sleep(0.02)
                
                # Send completion signal with classrooms (serialize datetime objects)
                serialized_classrooms = serialize_for_json(classrooms) if classrooms else None
                yield f"data: {json.dumps({'done': True, 'classrooms': serialized_classrooms})}\n\n"
                
            except Exception as e:
                print(f"Error in stream generation: {e}")
                import traceback
                traceback.print_exc()
                
                # Check if it's an API error (like 302 redirect or outage)
                error_str = str(e)
                if "302" in error_str or "outage" in error_str.lower() or "Moved Temporarily" in error_str:
                    user_friendly_error = "The AI service is currently unavailable. Please try again later."
                elif "API" in error_str or "api" in error_str.lower():
                    user_friendly_error = "There was an issue connecting to the AI service. Please try again."
                else:
                    user_friendly_error = "An error occurred while processing your request. Please try again."
                
                error_msg = json.dumps({"error": user_friendly_error, "done": True})
                yield f"data: {error_msg}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
            
    except Exception as e:
        print(f"Error in chat stream endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
