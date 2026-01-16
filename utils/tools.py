from langchain_core.tools import tool
from typing import Optional, List, Dict, Any
import httpx
import os

# Backend URL - should be set via environment variable
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")

@tool
async def query_classrooms_basic(
    seminar_setup: bool = False,
    lecture_setup: bool = False,
    group_learning: bool = False,
    class_size: Optional[int] = None,
    department_name: Optional[str] = None
) -> str:
    """
    Query classrooms based on essential criteria: class style (seminar, lecture, or group learning) and class size.
    Use this tool when you have collected the basic requirements from the user.
    
    Args:
        seminar_setup: Whether the classroom should support seminar-style teaching
        lecture_setup: Whether the classroom should support lecture-style teaching
        group_learning: Whether the classroom should support group learning
        class_size: The expected class size (number of students)
        department_name: The department name for context (optional)
    
    Returns:
        A formatted string with classroom results
    """
    try:
        # Build query parameters
        params = {
            "limit": 50
        }
        
        if seminar_setup:
            params["seminarSetup"] = "true"
        if lecture_setup:
            params["lectureSetup"] = "true"
        if group_learning:
            params["groupLearning"] = "true"
        if class_size:
            params["minSeats"] = max(1, class_size - 5)
            params["maxSeats"] = class_size + 10
            
        # Call backend classroom service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/api/classrooms",
                params=params,
                timeout=10.0
            )
            response.raise_for_status()
            
            data = response.json()
            classrooms = data.get("data", [])
            
            if not classrooms:
                return "No classrooms found matching the basic criteria. Try adjusting the requirements."
            
            # Format results for LLM
            result_text = f"Found {len(classrooms)} classrooms:\n\n"
            for classroom in classrooms[:10]:  # Show top 10
                result_text += f"- {classroom['building']} {classroom['room']}: {classroom['seatCount']} seats\n"
            
            return result_text
            
    except Exception as e:
        return f"Error querying classrooms: {str(e)}"

@tool
async def query_classrooms_with_amenities(
    seminar_setup: bool = False,
    lecture_setup: bool = False,
    group_learning: bool = False,
    class_size: Optional[int] = None,
    department_name: Optional[str] = None,
    projection_surface: Optional[str] = None,
    computer: Optional[str] = None,
    microphone: Optional[str] = None,
    zoom_room: Optional[str] = None,
    classroom_capture: Optional[bool] = None,
    group_learning_screens: Optional[bool] = None,
    white_board: Optional[bool] = None,
    chalk_board: Optional[bool] = None,
    dual_board_screen_use: Optional[bool] = None,
    group_learning_boards: Optional[bool] = None,
    teaching_station: Optional[str] = None,
    windows: Optional[bool] = None,
    ac: Optional[bool] = None,
    floor_type: Optional[str] = None,
    furniture: Optional[str] = None,
    film_screening: Optional[bool] = None
) -> str:
    """
    Query classrooms with specific amenities and features.
    Use this tool when the user has specified detailed requirements beyond just class style and size.
    
    Args:
        seminar_setup: Supports seminar-style teaching
        lecture_setup: Supports lecture-style teaching
        group_learning: Supports group learning
        class_size: Expected class size
        department_name: Department name (optional)
        projection_surface: Type of projection surface
        computer: Type of computer available
        microphone: Type of microphone system
        zoom_room: Type of Zoom room setup
        classroom_capture: Has classroom capture system
        group_learning_screens: Has group learning screens
        white_board: Has whiteboard
        chalk_board: Has chalkboard
        dual_board_screen_use: Supports dual board/screen use
        group_learning_boards: Has group learning boards
        teaching_station: Type of teaching station
        windows: Has windows
        ac: Has air conditioning
        floor_type: Type of floor
        furniture: Type of furniture
        film_screening: Supports film screening
    
    Returns:
        A formatted string with detailed classroom results
    """
    try:
        # Build query parameters with all filters
        params = {"limit": 3}
        
        # Essential criteria
        if seminar_setup:
            params["seminarSetup"] = "true"
        if lecture_setup:
            params["lectureSetup"] = "true"
        if group_learning:
            params["groupLearning"] = "true"
        if class_size:
            params["minSeats"] = max(1, class_size - 5)
            params["maxSeats"] = class_size + 10
            
        # Amenities
        if projection_surface:
            params["projectionSurface"] = projection_surface
        if computer:
            params["computer"] = computer
        if microphone:
            params["microphone"] = microphone
        if zoom_room:
            params["zoomRoom"] = zoom_room
        if classroom_capture is not None:
            params["classroomCapture"] = str(classroom_capture).lower()
        if group_learning_screens is not None:
            params["groupLearningScreens"] = str(group_learning_screens).lower()
        if white_board is not None:
            params["whiteBoard"] = str(white_board).lower()
        if chalk_board is not None:
            params["chalkBoard"] = str(chalk_board).lower()
        if dual_board_screen_use is not None:
            params["dualBoardScreenUse"] = str(dual_board_screen_use).lower()
        if group_learning_boards is not None:
            params["groupLearningBoards"] = str(group_learning_boards).lower()
        if teaching_station:
            params["teachingStation"] = teaching_station
        if windows is not None:
            params["windows"] = str(windows).lower()
        if ac is not None:
            params["ac"] = str(ac).lower()
        if floor_type:
            params["floorType"] = floor_type
        if furniture:
            params["furniture"] = furniture
        if film_screening is not None:
            params["filmScreening"] = str(film_screening).lower()
            
        # Call backend classroom service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/api/classrooms",
                params=params,
                timeout=10.0
            )
            response.raise_for_status()
            
            data = response.json()
            classrooms = data.get("data", [])
            
            if not classrooms:
                return "No classrooms found matching all the specified amenities. Consider relaxing some requirements."
            
            # Format detailed results
            result_text = f"Found {len(classrooms)} classroom(s) with your amenities:\n\n"
            for classroom in classrooms:
                result_text += f"- {classroom['building']} {classroom['room']}: {classroom['seatCount']} seats\n"
            
            return result_text
            
    except Exception as e:
        return f"Error querying classrooms with amenities: {str(e)}"

tools = [query_classrooms_basic, query_classrooms_with_amenities]
