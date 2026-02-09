# Quick Start Guide - Agent Service

## The Problem

If you're seeing the error message "I'm sorry, I encountered an error. Please try again or rephrase your question." when trying to chat with the agent from the frontend, it's likely because **the agent service is not running**.

## Solution: Start the Agent Service

### Option 1: Using the Startup Script (Easiest)

```bash
cd agent
./start.sh
```

This script will:
- Activate the virtual environment
- Install dependencies if needed
- Check for .env file
- Start the agent service on port 8000

### Option 2: Manual Start

1. **Navigate to the agent directory:**
   ```bash
   cd agent
   ```

2. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```
   (Note: The virtual environment is in `venv/`, not `.venv/` or `activate/venv/`)

3. **Install dependencies (if not already installed):**
   ```bash
   pip install -r requirements.txt
   ```

4. **Check your .env file:**
   Make sure you have a `.env` file with:
   - `OPENAI_API_KEY=your_key_here`
   - `BACKEND_URL=http://localhost:5000` (or your backend URL)
   - `PORT=8000` (optional, defaults to 8000)

5. **Start the agent service:**
   ```bash
   python app.py
   ```

You should see output like:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Verify It's Running

Open a new terminal and check:
```bash
curl http://localhost:8000/health
```

You should see: `{"status":"healthy"}`

## Troubleshooting

### Port 8000 Already in Use

If you get an error that port 8000 is already in use:

1. Find what's using it:
   ```bash
   lsof -i :8000
   ```

2. Either stop that process or change the port in your `.env` file:
   ```
   PORT=8001
   ```

3. Update your frontend `.env` file to match:
   ```
   VITE_AGENT_URL=http://localhost:8001
   ```

### Virtual Environment Issues

If you have trouble activating the virtual environment:

1. Make sure you're in the `agent` directory
2. The correct path is `venv/bin/activate` (not `.venv` or `activate/venv`)
3. If the venv doesn't exist, create it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### Missing Dependencies

If you get import errors:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Make sure your `.env` file has:
- `OPENAI_API_KEY` - Required for the LLM
- `BACKEND_URL` - URL of your backend API (default: http://localhost:5000)
- `PORT` - Port for the agent service (default: 8000)

## Architecture

The frontend calls the agent service directly:
- Frontend → Agent Service (port 8000)
- Agent Service → Backend API (for classroom data)

Make sure both the agent service and backend are running!
