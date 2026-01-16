from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

import os


load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError(
        "API key not found! Please set OPENAI_API_KEY environment variable."
    )


model = ChatOpenAI(
    model="gpt-5",
    api_key=openai_api_key
)