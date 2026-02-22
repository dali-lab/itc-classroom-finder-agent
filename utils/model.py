from langchain_dartmouth.llms import ChatDartmouth
from dotenv import load_dotenv
import os

load_dotenv()

dartmouth_chat_api_key = os.getenv("DARTMOUTH_CHAT_API_KEY")

if not dartmouth_chat_api_key:
    raise ValueError(
        "API key not found! Please set DARTMOUTH_CHAT_API_KEY environment variable."
    )

model = ChatDartmouth(
    dartmouth_chat_api_key=dartmouth_chat_api_key
)