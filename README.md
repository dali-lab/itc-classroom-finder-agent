# Simple Agent Template using LangGraph and Python

A simple ReAct agent template built with LangGraph that demonstrates how to create conversational AI agents with tool usage capabilities.

## Prerequisites

### Model Setup

This template requires a language model to function. You have several options:

#### Option 1: Local Model with Ollama (Recommended for Development)

1. **Install Ollama:**
   ```bash
   # macOS
   brew install ollama
   
   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Windows
   # Download from https://ollama.ai/download
   ```

2. **Download a model:**
   ```bash
   # Download a model (choose one based on your hardware)
   ollama pull llama3.2:3b        # Lightweight, good for testing
   ollama pull llama3.2:1b         # Very lightweight
   ollama pull qwen2.5:7b          # Good balance of performance/size
   ollama pull mistral:7b          # High quality
   ```

3. **Update the model in `utils/model.py`:**
   ```python
   model = ChatOllama(
       model="gpt-oss:20b",  # You need to use this model for tool executions
       temperature=0
   )
   ```

#### Option 2: OpenAI API (Requires API Key)

1. **Get an OpenAI API key** from [OpenAI Platform](https://platform.openai.com/api-keys)

2. **Set environment variable:**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
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

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the development server:**
   ```bash
   langgraph dev
   ```

3. **Access the LangGraph Studio:**
   - Open your browser to `http://localhost:8123`
   - This provides a visual interface to test and debug your agent
   - You can see the graph execution flow, inspect state, and test different inputs

### Key Features of Development Mode:

- **Hot Reload**: Automatically reloads when you change your code
- **Visual Debugging**: See the execution flow of your agent
- **State Inspection**: View the state at each step
- **Interactive Testing**: Test your agent with different inputs
- **Graph Visualization**: Visual representation of your agent's workflow

### Configuration

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

## Deployment Options

### Option 1: LangServe (Recommended for Production)

LangServe is the official deployment solution for LangChain applications:

1. **Install LangServe:**
   ```bash
   pip install langserve
   ```

2. **Create a deployment script (`deploy.py`):**
   ```python
   from langserve import add_routes
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