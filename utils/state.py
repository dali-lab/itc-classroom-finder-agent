from typing import Annotated, Sequence, TypedDict, Optional, List, Dict, Any
from langgraph.graph.message import add_messages
from langgraph.graph.ui import AnyUIMessage, ui_message_reducer

class CustomState(TypedDict):
    messages: Annotated[list, add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]
    remaining_steps: int
    classrooms: Optional[List[Dict[str, Any]]]  # Store classroom data for frontend
