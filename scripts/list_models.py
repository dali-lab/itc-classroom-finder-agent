from dotenv import load_dotenv; load_dotenv()
from langchain_dartmouth.llms import ChatDartmouth
import json, os
print('DARTMOUTH_CHAT_API_KEY set:', bool(os.getenv('DARTMOUTH_CHAT_API_KEY')))
try:
    result = ChatDartmouth().list()
    print(json.dumps(result, indent=2, default=str))
except Exception as e:
    print('Error:', e)
