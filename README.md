# Classroom Finder Agent using LangChain

A LangChain-based agent service that helps professors find suitable classrooms at Dartmouth College based on their teaching requirements.

## Overview

This agent replaces the hardcoded tool invocation approach with LangChain's built-in tool calling capabilities. It provides a FastAPI endpoint that the backend can call to process classroom search requests using natural language.

## Architecture

- Frontend -> Backend -> Agent Service
- Backend handles authentication and type validation
- Agent uses LangChain for intelligent tool selection
- Tools query the backend's classroom database

## Prerequisites

### Model Setup

This template uses OpenAI models via LangChain. You need an OpenAI API key.

1. **Get an OpenAI API key** from [OpenAI Platform](https://platform.openai.com/api-keys)

2. **Create .env file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Update `utils/model.py`:**
   ```python
   from langchain_openai import ChatOpenAI
   
   model = ChatOpenAI(
       model="gpt-3.5-turbo",
       temperature=0
   )
   ```

#### Option 3: Other Cloud Providers

For other providers (Anthropic, Google, etc.), update `utils/model.py` with the appropriate LangChain integration and set the required API keys.

## Development Mode

### Running with LangGraph Dev Server

LangGraph provides a development server that automatically reloads your graph when you make changes:

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and set:
   # - OPENAI_API_KEY
   # - BACKEND_URL (URL of the backend API, e.g., http://localhost:5000)
   # - PORT (agent service port, default: 8000)
   ```

## Running the Agent

### Option 1: FastAPI Server (Recommended for Production)

Run the FastAPI server that the backend will call:

```bash
python app.py
```

The agent will be available at `http://localhost:8000` with the following endpoints:
- `POST /chat` - Main chat endpoint
- `GET /health` - Health check endpoint

### Option 2: CLI Mode (For Testing)

Test the agent interactively in the terminal:

```bash
python main.py
```

This runs a simple chat loop where you can test the agent directly.

### Option 3: LangGraph Studio (For Development)

Use LangGraph Studio for visual debugging:

```bash
langgraph dev
```

## How It Works

1. Backend receives chat request from frontend with user authentication
2. Backend validates Dartmouth token and forwards to agent service
3. Agent processes messages using LangChain workflow
4. Agent decides whether to:
   - Gather more information from user
   - Call query_classrooms_basic tool for initial search
   - Call query_classrooms_with_amenities tool for detailed search
5. Tools make HTTP requests to backend classroom API
6. Agent formats results and returns to backend
7. Backend sends response to frontend

## Tools Available

- **query_classrooms_basic**: Search by class style and size
- **query_classrooms_with_amenities**: Search with detailed amenities

## Configuration

The `langgraph.json` file configures your graph:

```json
{
    "dependencies": ["./agent.py"],
    "graphs": {
        "react_agent_template": "./agent.py:workflow"
    },
    "env": "./.env"
}
```

   from fastapi import FastAPI
   from agent import workflow
   
   app = FastAPI()
   
   # Add the LangGraph workflow as a route
   add_routes(app, workflow, path="/agent")
   
   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8000)
   ```

3. **Run the deployment:**
   ```bash
   python deploy.py
   ```

4. **Access your deployed agent:**
   - API endpoint: `http://localhost:8000/agent`
   - Interactive docs: `http://localhost:8000/docs`

### Option 2: Docker Deployment

1. **Create a Dockerfile:**
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   
   CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Build and run:**
   ```bash
   docker build -t langgraph-agent .
   docker run -p 8000:8000 langgraph-agent
   ```

## How to Run

### Development Mode
```bash
# Start the development server on port 2024
langgraph dev --host 0.0.0.0 --port 2024

# Or use the default port (2024) with explicit host binding
langgraph dev --host 0.0.0.0

# Access the server using these URLs:
# - API Documentation: http://localhost:2024/docs
# - LangGraph Studio: https://smith.langchain.com/studio/?baseUrl=http://localhost:2024
# 
# Note: Use 'localhost' or '127.0.0.1' in browser URLs, NOT '0.0.0.0'
# The root path (/) returns 404 - use /docs for API documentation
```

### Production Mode
```bash
# Using LangServe
python deploy.py

# Or using Docker
docker run -p 8000:8000 langgraph-agent
```

## Project Structure

```
├── agent.py              # Main agent definition
├── langgraph.json        # LangGraph configuration
├── main.py              # Entry point for standalone usage
├── requirements.txt     # Python dependencies
├── utils/
│   ├── model.py         # Model configuration
│   ├── state.py         # State schema definition
│   └── tools.py         # Available tools for the agent
└── README.md            # This file
```

## Customization

### Adding New Tools

1. **Define your tool in `utils/tools.py`:**
   ```python
   from langchain_core.tools import tool
   
   @tool
   def your_custom_tool(input: str) -> str:
       """Description of what your tool does."""
       # Your tool logic here
       return result
   ```

2. **Add it to the agent in `agent.py`:**
   ```python
   from utils.tools import addition, your_custom_tool
   
   workflow = create_react_agent(
       # ... other parameters
       tools=[addition, your_custom_tool],
   )
   ```

### Modifying the System Prompt

Edit the `system_prompt` in `agent.py` to customize your agent's behavior:

```python
system_prompt = """Your custom system prompt here.
Define how your agent should behave, what it can do, and how it should respond.
"""
```

## Troubleshooting

### Common Issues

1. **Model not found**: Ensure your model is downloaded with Ollama or your API key is set correctly
2. **Import errors**: Make sure all dependencies are installed with `pip install -r requirements.txt`
3. **Port conflicts**: Change the port in your configuration if 8000 or 8123 are already in use

### Getting Help

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [Ollama Documentation](https://ollama.ai/docs)