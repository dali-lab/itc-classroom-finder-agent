from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
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
        
        # Invoke agent workflow
        response = workflow.invoke(
            {"messages": messages},
            config={"configurable": {"thread_id": thread_id}}
        )
        
        # Extract response
        if response and "messages" in response:
            last_message = response["messages"][-1]

            # Log all messages for debugging
            print(f"\n{'='*60}")
            print(f"[DEBUG] Total messages: {len(response['messages'])}")
            for i, msg in enumerate(response["messages"]):
                print(f"\n[DEBUG] Message {i}: type={msg.type}")
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        print(f"  [TOOL CALL] {tc['name']}({tc['args']})")
                if msg.type == "tool":
                    print(f"  [TOOL RESULT] name={msg.name}")
                    print(f"  [TOOL RESULT] content={msg.content[:300]}")
                    print(f"  [TOOL RESULT] artifact type={type(msg.artifact)}, value={msg.artifact}")
                if msg.type == "ai":
                    print(f"  [AI] content={msg.content[:200]}")
            print(f"{'='*60}\n")

            # Check if tool was called by inspecting message history
            tool_called = any(
                hasattr(msg, "tool_calls") and msg.tool_calls
                for msg in response["messages"]
            )

            # Extract classroom data from tool message artifacts
            classrooms = None
            for msg in reversed(response["messages"]):
                if msg.type == "tool" and hasattr(msg, "artifact") and msg.artifact:
                    classrooms = msg.artifact
                    print(f"[DEBUG] Extracted {len(classrooms)} classrooms from '{msg.name}' artifact")
                    break
            
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
