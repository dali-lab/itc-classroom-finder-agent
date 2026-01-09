from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os


load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError(
        "API key not found! Please set OPENAI_API_KEY environment variable."
    )

model = ChatOpenAI(
    api_key=openai_api_key
)