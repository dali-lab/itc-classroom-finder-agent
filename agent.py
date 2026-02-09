import uuid

from langchain.agents import create_agent
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

IMPORTANT rules for presenting classroom results:
- The classroom data is displayed to the user as interactive UI cards automatically. Do NOT repeat classroom details (names, buildings, seat counts, tables, etc.) in your text response.
- After a successful query, write a short conversational summary like "I found 8 classrooms that match your criteria." and offer to refine the search or answer questions.
- Never list classrooms in a table, bullet list, or any other text format. The UI handles that.

IMPORTANT rules for location/distance tools:
- When using validate_address or get_distance, always use full building names with "Hanover, NH 03755" (e.g. "Cummings Hall, Hanover, NH 03755").
- If a location lookup fails, do NOT keep retrying with different name variations. After at most 2 attempts, tell the user the address could not be found and ask them to provide a street address.
- Never make more than 3 total tool calls for a single address lookup.
"""

workflow = create_agent(
    model,
    tools=tools,
    system_prompt=system_prompt,
)

def chat():
    thread_id = str(uuid.uuid4())
    print("Classroom Finder Agent - Type 'quit' or 'exit' to end\n")
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
                # Log tool calls and tool results
                for msg in response["messages"]:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            print(f"\n--- TOOL CALL ---")
                            print(f"  Tool: {tc['name']}")
                            print(f"  Input: {tc['args']}")
                    if msg.type == "tool":
                        print(f"--- TOOL RESULT ---")
                        print(f"  Tool: {msg.name}")
                        print(f"  Output: {msg.content}")
                        print(f"-----------------")

                last_message = response["messages"][-1]
                print(f"\nAgent: {last_message.content}\n")
            else:
                print("\nAgent: (No response)\n")

        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    chat()

