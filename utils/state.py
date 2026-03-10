"""
State management for the classroom finder agent.
For now it just defines the necessary langgraph state type
"""

from typing import Annotated, Sequence, TypedDict
from langgraph.graph.message import add_messages
from langgraph.graph.ui import AnyUIMessage, ui_message_reducer

class CustomState(TypedDict):
    messages: Annotated[list, add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]
    remaining_steps: int
