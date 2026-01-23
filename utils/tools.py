from langchain_core.tools import tool
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "Supabase credentials not found! Please set SUPABASE_URL and SUPABASE_KEY in environment variables."
    )

# initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@tool
def query_classrooms_basic(
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
        # Build Supabase query
        query = supabase.table("Classroom").select("*")
        
        # Apply filters
        if seminar_setup:
            query = query.eq("seminarSetup", True)
        if lecture_setup:
            query = query.eq("lectureSetup", True)
        if group_learning:
            query = query.eq("groupLearning", True)
        if class_size:
            min_seats = max(1, class_size - 5)
            max_seats = class_size + 10
            query = query.gte("seatCount", min_seats).lte("seatCount", max_seats)
        
        # Execute query with limit
        response = query.limit(50).execute()
        classrooms = response.data
        
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
def query_classrooms_with_amenities(
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
        # Build Supabase query
        query = supabase.table("Classroom").select("*")
        
        # Essential criteria
        if seminar_setup:
            query = query.eq("seminarSetup", True)
        if lecture_setup:
            query = query.eq("lectureSetup", True)
        if group_learning:
            query = query.eq("groupLearning", True)
        if class_size:
            min_seats = max(1, class_size - 5)
            max_seats = class_size + 10
            query = query.gte("seatCount", min_seats).lte("seatCount", max_seats)
        
        # Amenities - string fields
        if projection_surface:
            query = query.eq("projectionSurface", projection_surface)
        if computer:
            query = query.eq("computer", computer)
        if microphone:
            query = query.eq("microphone", microphone)
        if zoom_room:
            query = query.eq("zoomRoom", zoom_room)
        if teaching_station:
            query = query.eq("teachingStation", teaching_station)
        if floor_type:
            query = query.eq("floorType", floor_type)
        if furniture:
            query = query.eq("furniture", furniture)
            
        # Amenities - boolean fields
        if classroom_capture is not None:
            query = query.eq("classroomCapture", classroom_capture)
        if group_learning_screens is not None:
            query = query.eq("groupLearningScreens", group_learning_screens)
        if white_board is not None:
            query = query.eq("whiteBoard", white_board)
        if chalk_board is not None:
            query = query.eq("chalkBoard", chalk_board)
        if dual_board_screen_use is not None:
            query = query.eq("dualBoardScreenUse", dual_board_screen_use)
        if group_learning_boards is not None:
            query = query.eq("groupLearningBoards", group_learning_boards)
        if windows is not None:
            query = query.eq("windows", windows)
        if ac is not None:
            query = query.eq("ac", ac)
        if film_screening is not None:
            query = query.eq("filmScreening", film_screening)
        
        # Execute query with limit
        response = query.limit(3).execute()
        classrooms = response.data
        
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
