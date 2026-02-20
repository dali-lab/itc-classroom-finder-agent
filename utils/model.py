from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain_dartmouth.llms import ChatDartmouth

import os


load_dotenv()
dartmouth_api_key = os.getenv("DARTMOUTH_API_KEY")


# model = ChatOpenAI(
#     model="gpt-5",
#     api_key=dartmouth_chat_api_key
# )

model = ChatDartmouth(dartmouth_chat_api_key=dartmouth_api_key)