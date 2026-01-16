import uuid

from langgraph.prebuilt import create_react_agent
from utils.model import model
from utils.tools import tools


system_prompt = """You are a helpful classroom finder assistant for Dartmouth College.

Your goal is to help professors find the best classroom for their teaching needs.

To find a classroom, you need to gather THREE essential pieces of information:
1. Class style: Is it a seminar, lecture, or group learning setup?
2. Class size: How many students will attend?
3. Department name: What department is this for? (for context)

Once you have these basics, use the query_classrooms_basic tool to show initial options.

If the user wants more specific features (like projectors, whiteboards, air conditioning, etc.),
ask about those amenities and then use the query_classrooms_with_amenities tool.

Be friendly, concise, and guide the conversation naturally.
Do not make assumptions - always confirm requirements with the user first.

When presenting results, describe them in a helpful way and offer to search again with different criteria if needed.
"""

workflow = create_react_agent(
    model, 
    tools=tools,
    prompt=system_prompt,
)

async def chat():
    thread_id = str(uuid.uuid4())
    while True:
        user_input = input("User: ").strip()

        if user_input.lower() in ['quit', 'exit']:
            print("Ending chat session.")
            break

        if not user_input:
            continue

        try:
            response = workflow.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config={"configurable": {"thread_id": thread_id}}
            )

            # Extract and print the agent's response
            if response and "messages" in response:
                last_message = response["messages"][-1]
                print(f"\nAgent: {last_message.content}\n")
            else:
                print("\nAgent: (No response)\n")

        except Exception as e:
            print(f"\nError: {e}\n")
